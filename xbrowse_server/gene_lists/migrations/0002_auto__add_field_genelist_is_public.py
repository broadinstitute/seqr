# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'GeneList.is_public'
        db.add_column('gene_lists_genelist', 'is_public',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'GeneList.is_public'
        db.delete_column('gene_lists_genelist', 'is_public')


    models = {
        'gene_lists.genelist': {
            'Meta': {'object_name': 'GeneList'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'})
        },
        'gene_lists.genelistitem': {
            'Meta': {'object_name': 'GeneListItem'},
            'gene_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'gene_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gene_lists.GeneList']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['gene_lists']