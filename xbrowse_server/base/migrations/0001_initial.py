# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('gene_lists', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CausalVariant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('variant_type', models.CharField(default=b'', max_length=10)),
                ('xpos', models.BigIntegerField(null=True)),
                ('ref', models.TextField(null=True)),
                ('alt', models.TextField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Cohort',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cohort_id', models.CharField(default=b'', max_length=140, blank=True)),
                ('display_name', models.CharField(default=b'', max_length=140, blank=True)),
                ('short_description', models.CharField(default=b'', max_length=140, blank=True)),
                ('variant_stats_json', models.TextField(default=b'', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Family',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('family_id', models.CharField(default=b'', max_length=140, blank=True)),
                ('family_name', models.CharField(default=b'', max_length=140, blank=True)),
                ('short_description', models.CharField(default=b'', max_length=500, blank=True)),
                ('about_family_content', models.TextField(default=b'', blank=True)),
                ('pedigree_image', models.ImageField(height_field=b'pedigree_image_height', width_field=b'pedigree_image_width', null=True, upload_to=b'pedigree_images', blank=True)),
                ('pedigree_image_height', models.IntegerField(default=0, null=True, blank=True)),
                ('pedigree_image_width', models.IntegerField(default=0, null=True, blank=True)),
                ('analysis_status', models.CharField(default=b'I', max_length=1, choices=[(b'S', b'Solved'), (b'I', b'In Progress'), (b'Q', b'Waiting for data')])),
                ('causal_inheritance_mode', models.CharField(default=b'unknown', max_length=20)),
                ('relatedness_matrix_json', models.TextField(default=b'', blank=True)),
                ('variant_stats_json', models.TextField(default=b'', blank=True)),
                ('has_before_load_qc_error', models.BooleanField(default=False)),
                ('before_load_qc_json', models.TextField(default=b'', blank=True)),
                ('has_after_load_qc_error', models.BooleanField(default=False)),
                ('after_load_qc_json', models.TextField(default=b'', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FamilyGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(max_length=100)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('families', models.ManyToManyField(to='base.Family')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FamilyImageSlide',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('image', models.ImageField(null=True, upload_to=b'family_image_slides', blank=True)),
                ('order', models.FloatField(default=0.0)),
                ('caption', models.CharField(default=b'', max_length=300, blank=True)),
                ('family', models.ForeignKey(to='base.Family')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FamilySearchFlag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('xpos', models.BigIntegerField()),
                ('ref', models.TextField()),
                ('alt', models.TextField()),
                ('flag_type', models.CharField(max_length=1, choices=[(b'C', b'Likely causal'), (b'R', b'Flag for review'), (b'N', b'Other note')])),
                ('suggested_inheritance', models.SlugField(default=b'', max_length=40)),
                ('search_spec_json', models.TextField(default=b'', blank=True)),
                ('date_saved', models.DateTimeField()),
                ('note', models.TextField(default=b'', blank=True)),
                ('family', models.ForeignKey(blank=True, to='base.Family', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('indiv_id', models.SlugField(default=b'', max_length=140, blank=True)),
                ('nickname', models.CharField(default=b'', max_length=140, blank=True)),
                ('gender', models.CharField(default=b'U', max_length=1, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'U', b'Unknown')])),
                ('affected', models.CharField(default=b'U', max_length=1, choices=[(b'A', b'Affected'), (b'N', b'Unaffected'), (b'U', b'Unknown')])),
                ('maternal_id', models.SlugField(default=b'', max_length=140, blank=True)),
                ('paternal_id', models.SlugField(default=b'', max_length=140, blank=True)),
                ('other_notes', models.TextField(default=b'', null=True, blank=True)),
                ('coverage_file', models.CharField(default=b'', max_length=200, blank=True)),
                ('exome_depth_file', models.CharField(default=b'', max_length=200, blank=True)),
                ('vcf_id', models.CharField(default=b'', max_length=40, blank=True)),
                ('family', models.ForeignKey(blank=True, to='base.Family', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IndividualPhenotype',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('boolean_val', models.NullBooleanField()),
                ('float_val', models.FloatField(null=True, blank=True)),
                ('individual', models.ForeignKey(to='base.Individual')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project_id', models.SlugField(default=b'', unique=True, max_length=140, blank=True)),
                ('project_name', models.CharField(default=b'', max_length=140, blank=True)),
                ('description', models.TextField(default=b'', blank=True)),
                ('is_public', models.BooleanField(default=False)),
                ('last_accessed_date', models.DateTimeField(null=True, blank=True)),
                ('default_control_cohort', models.CharField(default=b'', max_length=100, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectCollaborator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('collaborator_type', models.CharField(default=b'collaborator', max_length=20, choices=[(b'manager', b'Manager'), (b'collaborator', b'Collaborator')])),
                ('project', models.ForeignKey(to='base.Project')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectGeneList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('gene_list', models.ForeignKey(to='gene_lists.GeneList')),
                ('project', models.ForeignKey(to='base.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectPhenotype',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(default=b'pheno', max_length=140)),
                ('name', models.CharField(default=b'', max_length=140)),
                ('category', models.CharField(max_length=20, choices=[(b'disease', b'Disease'), (b'clinial_observation', b'Clinical Observation'), (b'other', b'Other')])),
                ('datatype', models.CharField(max_length=20, choices=[(b'bool', b'Boolean'), (b'number', b'Number')])),
                ('project', models.ForeignKey(to='base.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.SlugField()),
                ('title', models.CharField(default=b'', max_length=300)),
                ('color', models.CharField(default=b'', max_length=10)),
                ('project', models.ForeignKey(to='base.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReferencePopulation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(default=b'')),
                ('name', models.CharField(default=b'', max_length=100)),
                ('file_type', models.CharField(default=b'', max_length=50)),
                ('file_path', models.CharField(default=b'', max_length=500)),
                ('is_public', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('display_name', models.CharField(default=b'', max_length=100, blank=True)),
                ('set_password_token', models.CharField(default=b'', max_length=40, blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VariantNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_saved', models.DateTimeField()),
                ('note', models.TextField(default=b'', blank=True)),
                ('xpos', models.BigIntegerField()),
                ('ref', models.TextField()),
                ('alt', models.TextField()),
                ('family', models.ForeignKey(blank=True, to='base.Family', null=True)),
                ('individual', models.ForeignKey(blank=True, to='base.Individual', null=True)),
                ('project', models.ForeignKey(to='base.Project')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VariantTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('xpos', models.BigIntegerField()),
                ('ref', models.TextField()),
                ('alt', models.TextField()),
                ('family', models.ForeignKey(to='base.Family', null=True)),
                ('project_tag', models.ForeignKey(to='base.ProjectTag')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VCFFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file_path', models.CharField(default=b'', max_length=500, blank=True)),
                ('needs_reannotate', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='project',
            name='collaborators',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, null=True, through='base.ProjectCollaborator', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='gene_lists',
            field=models.ManyToManyField(to='gene_lists.GeneList', through='base.ProjectGeneList'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='private_reference_populations',
            field=models.ManyToManyField(to='base.ReferencePopulation', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='individualphenotype',
            name='phenotype',
            field=models.ForeignKey(to='base.ProjectPhenotype'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='individual',
            name='project',
            field=models.ForeignKey(blank=True, to='base.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='individual',
            name='vcf_files',
            field=models.ManyToManyField(to='base.VCFFile', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='familygroup',
            name='project',
            field=models.ForeignKey(to='base.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='family',
            name='project',
            field=models.ForeignKey(blank=True, to='base.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cohort',
            name='individuals',
            field=models.ManyToManyField(to='base.Individual'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cohort',
            name='project',
            field=models.ForeignKey(blank=True, to='base.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='causalvariant',
            name='family',
            field=models.ForeignKey(to='base.Family', null=True),
            preserve_default=True,
        ),
    ]
