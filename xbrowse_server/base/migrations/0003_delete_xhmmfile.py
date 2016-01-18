# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_auto_20160117_1843'),
    ]

    operations = [
        migrations.DeleteModel(
            name='XHMMFile',
        ),
    ]
