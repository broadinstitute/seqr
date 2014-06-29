# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Individual.last_updated_from_xbrowse'
        db.add_column('base_individual', 'last_updated_from_xbrowse',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 8, 8, 0, 0)),
                      keep_default=False)

        # Adding field 'Project.last_updated_from_xbrowse'
        db.add_column('base_project', 'last_updated_from_xbrowse',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 8, 8, 0, 0)),
                      keep_default=False)

        # Adding field 'Family.last_updated_from_xbrowse'
        db.add_column('base_family', 'last_updated_from_xbrowse',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 8, 8, 0, 0)),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Individual.last_updated_from_xbrowse'
        db.delete_column('base_individual', 'last_updated_from_xbrowse')

        # Deleting field 'Project.last_updated_from_xbrowse'
        db.delete_column('base_project', 'last_updated_from_xbrowse')

        # Deleting field 'Family.last_updated_from_xbrowse'
        db.delete_column('base_family', 'last_updated_from_xbrowse')


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
        'base.family': {
            'Meta': {'object_name': 'Family'},
            'about_family_content': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'family_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 8, 8, 0, 0)'}),
            'pedigree_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'pedigree_image_height': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'pedigree_image_width': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 8, 8, 0, 0)'}),
            'maternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'paternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.milestone': {
            'Meta': {'object_name': 'Milestone'},
            'added_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'date_of_milestone': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.project': {
            'Meta': {'object_name': 'Project'},
            'coll_name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.UserGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated_from_xbrowse': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 8, 8, 0, 0)'}),
            'project_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'unique': 'True', 'max_length': '140', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.savedinheritance': {
            'Meta': {'object_name': 'SavedInheritance'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inheritance_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.savedvariantquery': {
            'Meta': {'object_name': 'SavedVariantQuery'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'population': ('django.db.models.fields.CharField', [], {'default': "'AF'", 'max_length': '140', 'blank': 'True'}),
            'variant_query_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        'base.usergroup': {
            'Meta': {'object_name': 'UserGroup'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'group_id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['base.UserGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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