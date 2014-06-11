# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'GeneListItem.description'
        db.add_column(u'gene_lists_genelistitem', 'description',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'GeneListItem.description'
        db.delete_column(u'gene_lists_genelistitem', 'description')


    models = {
        u'gene_lists.genelist': {
            'Meta': {'object_name': 'GeneList'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'})
        },
        u'gene_lists.genelistitem': {
            'Meta': {'object_name': 'GeneListItem'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'gene_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'gene_list': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gene_lists.GeneList']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['gene_lists']