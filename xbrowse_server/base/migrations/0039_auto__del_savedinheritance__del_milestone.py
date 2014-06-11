# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'SavedInheritance'
        db.delete_table('base_savedinheritance')

        # Deleting model 'Milestone'
        db.delete_table('base_milestone')


    def backwards(self, orm):
        # Adding model 'SavedInheritance'
        db.create_table('base_savedinheritance', (
            ('name', self.gf('django.db.models.fields.CharField')(default='', max_length=140, blank=True)),
            ('family', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.Family'], null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(default='', max_length=140, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('inheritance_json', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('base', ['SavedInheritance'])

        # Adding model 'Milestone'
        db.create_table('base_milestone', (
            ('family', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.Family'], null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(default='', max_length=140, blank=True)),
            ('date_of_milestone', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('added_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('base', ['Milestone'])


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'base.diseasegenelist': {
            'Meta': {'object_name': 'DiseaseGeneList'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_admins': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['base.UserProfile']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.family': {
            'Meta': {'object_name': 'Family'},
            'about_family_content': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'after_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'before_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'coll_name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'date_loaded': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 28, 0, 0)'}),
            'exomes_loaded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'family_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'has_after_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_before_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_cohort': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 28, 0, 0)'}),
            'needs_inheritance_update': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'pedigree_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'pedigree_image_height': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'pedigree_image_width': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'relatedness_matrix_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'variant_stats_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        'base.flag': {
            'Meta': {'object_name': 'Flag'},
            'alt': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'analysis_type': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'bp1': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'chr': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inheritance_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'oid_string': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '24'}),
            'reason_for_flag': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'ref': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'search_profile_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'base.individual': {
            'Meta': {'object_name': 'Individual'},
            'affected': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'has_exome': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 28, 0, 0)'}),
            'maternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'paternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.project': {
            'Meta': {'object_name': 'Project'},
            'date_loaded': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 28, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.UserGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 28, 0, 0)'}),
            'project_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'unique': 'True', 'max_length': '140', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.usergroup': {
            'Meta': {'object_name': 'UserGroup'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'group_id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['base.UserGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projects_can_edit': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'can_edit_profiles'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['base.Project']"}),
            'projects_can_view': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'can_view_profiles'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['base.Project']"}),
            'set_password_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
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