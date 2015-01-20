# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BAMFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('indiv_id', models.CharField(max_length=100)),
                ('storage_mode', models.CharField(max_length=20, choices=[(b'local', b'Local'), (b'network', b'Network')])),
                ('file_path', models.TextField()),
                ('network_url', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='XHMMFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file_path', models.CharField(default=b'', max_length=500, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
