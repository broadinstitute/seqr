# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(max_length=40)),
                ('name', models.CharField(max_length=140)),
                ('description', models.TextField()),
                ('is_public', models.BooleanField(default=False)),
                ('last_updated', models.DateTimeField(null=True, blank=True)),
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GeneListItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('gene_id', models.CharField(max_length=20)),
                ('description', models.TextField(default=b'')),
                ('gene_list', models.ForeignKey(to='gene_lists.GeneList')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
