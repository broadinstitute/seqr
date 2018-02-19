# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-19 13:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0042_vcffile_sample_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='individual',
            name='guid',
        ),
        migrations.AddField(
            model_name='individual',
            name='cnv_bed_file',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AlterField(
            model_name='individual',
            name='bam_file_path',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AlterField(
            model_name='individual',
            name='coverage_file',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AlterField(
            model_name='individual',
            name='exome_depth_file',
            field=models.TextField(blank=True, default=b''),
        ),
    ]
