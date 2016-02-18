# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_delete_xhmmfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='created_date',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='family',
            name='analysis_status',
            field=models.CharField(default=b'I', max_length=1, choices=[(b'S', (b'Solved', b'fa-check-square-o')), (b'S_kgfp', (b'Solved - known gene for phenotype', b'fa-check-square-o')), (b'S_kgdp', (b'Solved - gene linked to different phenotype', b'fa-check-square-o')), (b'S_ng', (b'Solved - novel gene', b'fa-check-square-o')), (b'Sc_kgfp', (b'Strong candidate - known gene for phenotype', b'fa-check-square-o')), (b'Sc_kgdp', (b'Strong candidate - gene linked to different phenotype', b'fa-check-square-o')), (b'Sc_ng', (b'Strong candidate - novel gene', b'fa-check-square-o')), (b'Rncc', (b'Reviewed, no clear candidate', b'fa-check-square-o')), (b'I', (b'Analysis in Progress', b'fa-square-o')), (b'Q', (b'Waiting for data', b'fa-clock-o'))]),
            preserve_default=True,
        ),
    ]
