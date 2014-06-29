# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Individual'
        db.create_table('base_individual', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('indiv_id', self.gf('django.db.models.fields.SlugField')(default='', max_length=140, blank=True)),
            ('family', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.Family'], null=True, blank=True)),
            ('nickname', self.gf('django.db.models.fields.CharField')(default='', max_length=140, blank=True)),
        ))
        db.send_create_signal('base', ['Individual'])


    def backwards(self, orm):
        # Deleting model 'Individual'
        db.delete_table('base_individual')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'base.family': {
            'Meta': {'object_name': 'Family'},
            'family_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'})
        },
        'base.individual': {
            'Meta': {'object_name': 'Individual'},
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.project': {
            'Meta': {'object_name': 'Project'},
            'coll_name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'unique': 'True', 'max_length': '140', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['base']