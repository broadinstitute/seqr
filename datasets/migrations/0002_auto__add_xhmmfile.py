# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'XHMMFile'
        db.create_table(u'datasets_xhmmfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file_path', self.gf('django.db.models.fields.CharField')(default='', max_length=500, blank=True)),
        ))
        db.send_create_signal(u'datasets', ['XHMMFile'])


    def backwards(self, orm):
        # Deleting model 'XHMMFile'
        db.delete_table(u'datasets_xhmmfile')


    models = {
        u'datasets.bamfile': {
            'Meta': {'object_name': 'BAMFile'},
            'file_path': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'network_url': ('django.db.models.fields.TextField', [], {}),
            'storage_mode': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'datasets.xhmmfile': {
            'Meta': {'object_name': 'XHMMFile'},
            'file_path': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['datasets']