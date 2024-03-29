# Generated by Django 3.2.18 on 2023-10-11 20:02

import django.contrib.postgres.fields
from django.db import migrations, models


def populate_omim_list(apps, schema_editor):
    Family = apps.get_model('seqr', 'Family')
    db_alias = schema_editor.connection.alias

    families = Family.objects.using(db_alias).filter(
        post_discovery_omim_number__isnull=False).exclude(post_discovery_omim_number='')
    for f in families:
        f.post_discovery_omim_numbers = [int(o.strip()) for o in f.post_discovery_omim_number.split(',')]
    Family.objects.using(db_alias).bulk_update(families, ['post_discovery_omim_numbers'])


def populate_omim_string(apps, schema_editor):
    Family = apps.get_model('seqr', 'Family')
    db_alias = schema_editor.connection.alias

    families = Family.objects.using(db_alias).filter(post_discovery_omim_numbers__len__gt=0)
    for f in families:
        f.post_discovery_omim_number = ', '.join([str(n) for n in f.post_discovery_omim_numbers])
    Family.objects.using(db_alias).bulk_update(families, ['post_discovery_omim_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('seqr', '0055_alter_sample_tissue_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='family',
            name='post_discovery_omim_numbers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), default=list, size=None),
        ),
        migrations.RunPython(populate_omim_list, reverse_code=populate_omim_string),
        migrations.RemoveField(
            model_name='family',
            name='post_discovery_omim_number',
        ),
    ]
