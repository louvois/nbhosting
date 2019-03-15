# pylint: disable=c0111, w1203

from pathlib import Path
import subprocess

from importlib.util import (
    spec_from_file_location, module_from_spec)

from nbh_main.settings import NBHROOT, logger

from .model_track import Track, generic_track
from .model_track import write_tracks, read_tracks
from .model_mapping import StaticMapping

# this is what we expect to find in a course custom tracks.py
from typing import List
CourseTracks = List[Track]


class CourseDir:

    def __init__(self, coursename):
        self.coursename = coursename
        self._probe_settings()
        self._notebooks = None
        self._tracks = None


    def is_valid(self):
        return self.git_dir.exists() and self.git_dir.is_dir()
    def __repr__(self):
        return self.coursename

    def __len__(self):
        return len(self.notebooks())


    def _notebooks_dir(self):
        return NBHROOT / "courses" / self.coursename
    notebooks_dir = property(_notebooks_dir)

    def _git_dir(self):
        return NBHROOT / "courses-git" / self.coursename
    git_dir = property(_git_dir)

    def _static_dir(self):
        return NBHROOT / "static" / self.coursename
    static_dir = property(_static_dir)

    def _build_dir(self):
        return NBHROOT / "images" / self.coursename
    build_dir = property(_build_dir)


    def customized(self, filename):
        """
        given a filename, search this:
        * first in nbhroot/local/coursename/<filename>
        * second in nbhroot/courses-git/coursename/nbhosting/<filename>

        returns a Path instance, or None
        """
        c1 = NBHROOT / "local" / self.coursename / filename
        c2 = self.git_dir / "nbhosting" / filename

        logger.debug(f"{self}.customized({filename}):\n{c1}\n{c2}")

        for c in (c1, c2):
            if c.exists():
                return c
        return None


    # for templating
    def length(self):
        """
        number of sections
        """
        return len(self)

    def notebooks(self):
        """
        sorted list of notebook paths
        """
        if self._notebooks is None:
            self._notebooks = self._probe_sorted_notebooks()
        return self._notebooks

    @staticmethod
    def _probe_notebooks_in_dir(root):
        absolute_notebooks = root.glob("**/*.ipynb")
        # relative notebooks without extension
        return (
            notebook.relative_to(root).with_suffix("")
            for notebook in absolute_notebooks
            if 'ipynb_checkpoints' not in str(notebook)
        )

    def _probe_sorted_notebooks(self):
        return sorted(
            self._probe_notebooks_in_dir(self.notebooks_dir)
        )


    def probe_student_notebooks(self, student):
        root = NBHROOT / "students" / student / self.coursename
        return self._probe_notebooks_in_dir(root)



    def student_homes(self):
        """
        return the number of students who have that course in their home dir
        """
        student_course_dirs = (
            NBHROOT / "students").glob(f"*/{self.coursename}")
        # can't use len() on a generator
        return sum((1 for _ in student_course_dirs), 0)


    # check course-provided tracks and provide reasonable defaults
    # returns a Track object for a given track
    def _check_tracks(self, tracks: CourseTracks):
        type_ok = True
        if not isinstance(tracks, list):
            type_ok = False
        elif not all(isinstance(v, Track) for v in tracks):
            type_ok = False
        if not type_ok:
            logger.error("{self}: misformed tracks()")
        return type_ok


    # locate a Track corresponding to trackaname in tracks
    def _locate_track(self, tracks: CourseTracks, trackname) -> Track:
        for item in tracks:
            if item.name == trackname:
                return item
        # find some default
        if tracks:
            logger.warning(f"{self} has no {trackname} track - returning first track")
            return tracks[0]
        logger.warning("{self} has no track, returning generic")
        return generic_track(self)


    # actually call course-specific tracks()
    # return default strategy if missing or unable to run
    def _fetch_course_custom_tracks(self):
        """
        locate and load <course>/nbhosting/tracks.py

        objective is to make this customizable so that some
        notebooks in the repo can be ignored
        and the others organized along different view points

        the tracks() function will receive self as its single parameter
        it is expected to return a dictionary
           track_name -> Track instance
        see flotpython/courses/nbhosting/tracks.py for a realistic example

        the keys in this dictionary are used in the web interface
        to propose the list of available tracks

        absence of tracks.py, or inability to run it, triggers
        the default policy (per directory) implemented in model_track.py
        """

        course_tracks_py = self.customized("tracks.py")

        if course_tracks_py:
            modulename = (f"{self.coursename}_tracks"
                          .replace("-", "_"))
            try:
                logger.debug(
                    f"{self} loading module {course_tracks_py}")
                spec = spec_from_file_location(
                    modulename,
                    course_tracks_py,
                )
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                tracks_fun = module.tracks
                logger.debug(
                    f"triggerring {tracks_fun.__qualname__}()"
                )
                tracks = tracks_fun(self)
                if self._check_tracks(tracks):
                    return tracks
            except Exception:                           # pylint: disable=w0703
                logger.exception(
                    f"{self} could not do load custom tracks")
            finally:
                # make sure to reload the python code next time
                # we will need it, in case the course has published an update
                import sys
                if modulename in sys.modules:
                    del sys.modules[modulename]
        else:
            logger.info(
                f"{self} no tracks.py hook found")
        logger.warning(f"{self} resorting to generic filesystem-based track")
        return [generic_track(self)]


    def tracks(self):
        """
        returns a list of known tracks

        does this optimally, first use memory cache,
        disk cache in courses/<coursename>/.tracks.json
        and only then triggers course-specific tracks.py if provided
        """
        # in memory ?
        if self._tracks is not None:
            return self._tracks
        # in cache ?
        tracks_path = self.notebooks_dir / ".tracks.json"
        if tracks_path.exists():
            logger.debug(f"{tracks_path} found")
            tracks = read_tracks(self, tracks_path)
            self._tracks = tracks
            return tracks
        # compute from course
        logger.debug(f"{tracks_path} not found - recomputing")
        tracks = self._fetch_course_custom_tracks()
        self._tracks = tracks
        write_tracks(tracks, tracks_path)
        return tracks


    def tracknames(self):
        """
        returns the list of supported track names
        """
        return [track.name for track in self.tracks()]


    def track(self, trackname):
        """
        returns a Track object that maps that trackname
        """
        return self._locate_track(self.tracks(), trackname)


    def _probe_settings(self):
        notebooks_dir = self.notebooks_dir

        self.static_mappings = []
        custom_static_mappings = self.customized("static-mappings")
        if not custom_static_mappings:
            self.static_mappings = StaticMapping.defaults()
        else:
            try:
                with custom_static_mappings.open() as storage:
                    for line in storage:
                        mapping = StaticMapping(line)
                        if mapping:
                            self.static_mappings.append(mapping)
            except FileNotFoundError:
                # unfortunately this goes to stdout and
                # screws up the expose-static-* business
                #logger.info(f"mappings file not found {path}")
                self.static_mappings = StaticMapping.defaults()
            except Exception as exc:
                logger.exception(f"could not load static-mappings for {self}")
                self.static_mappings = StaticMapping.defaults()

        # store in raw format for nbh script
        with (self.notebooks_dir / ".static-mappings").open('w') as raw:
            for static_mapping in self.static_mappings:
                print(static_mapping.expose(self),
                      file=raw)
        toplevels = StaticMapping.static_toplevels(
            self.static_mappings
        )
        with (self.notebooks_dir / ".static-toplevels").open('w') as raw:
            for toplevel in toplevels:
                print(toplevel, file=raw)


        try:
            with (notebooks_dir / ".image").open() as storage:
                self.image = storage.read().strip()
        except Exception as exc:
            self.image = f"-- undefined -- {exc}"


        try:
            with (notebooks_dir / ".staff").open() as storage:
                self.staff = {
                    line.strip() for line in storage if line}
        except Exception:
            self.staff = set()


        try:
            with (notebooks_dir / ".giturl").open() as storage:
                self.giturl = storage.read().strip()
        except Exception as exc:
            self.giturl = f"-- undefined -- {exc}"


    def image_hash(self, docker_proxy):
        """
        the hash of the image that should be used for containers
        in this course
        or None if something goes wrong
        """
        try:
            return docker_proxy.images.get(self.image).id
        except:
            logger.exception("Can't figure image hash")
            return


    def _run_nbh_manage(self, subcommand, *args, **run_args):
        return self._run_nbh(subcommand, *args, manage=True, **run_args)

    def _run_nbh(self, subcommand, *args, manage=False, **run_args):
        """
        return an instance of subprocess.CompletedProcess

        Parameters:
          manage: the default is to call pain nbh; when manage is set to True,
            the `nbh-manage` command is used instead
          args: additional arguments to subcommand
          run_args: additional arguments to subprocess.run(); typically
            *encoding="utf-8"* is useful when text output is expected

        """
        main = "nbh" if not manage else "nbh-manage"
        command = [main, subcommand, self.coursename] + list(args)
        return subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **run_args)

    def update_from_git(self):
        return self._run_nbh("course-update-from-git", encoding="utf-8")
    def build_image(self):
        return self._run_nbh_manage("course_build_image", encoding="utf-8")
    def clear_staff(self):
        return self._run_nbh("course-clear-staff", encoding="utf-8")
    # because nbh-manage is django's manage.py we must use underscores
    def show_tracks(self):
        return self._run_nbh_manage("course_show_tracks", encoding="utf-8")