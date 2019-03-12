"""
Django settings for nbhosting project.

Generated by 'django-admin startproject' using Django 1.10.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

# pylint: disable=c0103

import os
import logging
from pathlib import Path

########## load sitesettings.py module that is **NOT** managed under git
# see sitesettings.py.example for a template
import nbh_main.sitesettings as sitesettings      # pylint: disable=c0414

from .sitesettings import (                             # pylint: disable=w0611
    SECRET_KEY,
    ALLOWED_HOSTS,
    DEBUG,
)

from .loggers import init_loggers


########## production vs devel
DEVEL = False
if os.getuid() == 0:
    # typically /nbhosting/logs
    LOGS_DIR = Path(sitesettings.nbhroot) / 'logs'
    # typically /root/nbhosting
    BASE_DIR = Path(sitesettings.srcroot)
else:
    # just a convenience for devel boxes
    # e.g. /users/tparment/git/nbhosting/nbhosting
    django_root = Path(__file__).parents[1]
    sitesettings.nbhroot = str(django_root / 'fake-root')
    # some provisions for devel mode
    LOGS_DIR = Path.cwd()
    # .parents[0] is dirname(f)
    # .parents[1] is dirname(dirname(f))
    BASE_DIR = Path(__file__).parents[1]

    # have the static files served in devel mode
    STATICFILES_DIRS = (str(BASE_DIR / "assets"), )
    DEVEL = True

NBHROOT = Path(sitesettings.nbhroot)

# this will create <root>/logs - and thus <root> - if needed
init_loggers(LOGS_DIR, DEBUG)
logger = logging.getLogger('nbhosting')
monitor_logger = logging.getLogger('monitor')

############################################################

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/


# SECRET_KEY = 'must-be-defined-in-sitesettings.py'
# you need to define DEBUG in sitesettings.py
# you need to define ALLOWED_HOSTS in sitesettings.py

# Application definition

INSTALLED_APPS = [
    'nbh_main.apps.MainConfig',
    'nbhosting.courses.apps.CoursesConfig',
    'nbhosting.stats.apps.StatsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

X_FRAME_OPTIONS = 'ALLOWALL'

ROOT_URLCONF = 'nbh_main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            './templates',
            # mostly for mass-register.py
            '.',
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nbh_main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# this sqlite3 database will contain the account info
# for the admin
# typically in /nbhosting/db.sqlite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/assets/'
STATIC_ROOT = '/var/nginx/nbhosting/assets/'

#################### back to django defaults, no longer a /nbh/ barrier
LOGIN_REDIRECT_URL = '/welcome/'
LOGIN_URL =          '/accounts/login/'
