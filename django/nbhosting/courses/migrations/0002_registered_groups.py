# Generated by Django 2.2.3 on 2019-10-30 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coursedir',
            name='registered_users',
        ),
        migrations.AddField(
            model_name='coursedir',
            name='registered_groups',
            field=models.ManyToManyField(related_name='courses_registered', to='auth.Group'),
        ),
    ]
