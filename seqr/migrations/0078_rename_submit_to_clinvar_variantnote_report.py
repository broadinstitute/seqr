# Generated by Django 4.2.16 on 2024-11-19 15:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seqr', '0077_alter_rnasample_tissue_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='variantnote',
            old_name='submit_to_clinvar',
            new_name='report',
        ),
    ]
