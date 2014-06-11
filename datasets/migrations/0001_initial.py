# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BAMFile'
        db.create_table(u'datasets_bamfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('indiv_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('storage_mode', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('file_path', self.gf('django.db.models.fields.TextField')()),
            ('network_url', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'datasets', ['BAMFile'])


    def backwards(self, orm):
        # Deleting model 'BAMFile'
        db.delete_table(u'datasets_bamfile')


    models = {
        u'datasets.bamfile': {
            'Meta': {'object_name': 'BAMFile'},
            'file_path': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'network_url': ('django.db.models.fields.TextField', [], {}),
            'storage_mode': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['datasets']