# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GeneList'
        db.create_table('gene_lists_genelist', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=40)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('gene_lists', ['GeneList'])

        # Adding model 'GeneListItem'
        db.create_table('gene_lists_genelistitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('gene_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('gene_list', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gene_lists.GeneList'])),
        ))
        db.send_create_signal('gene_lists', ['GeneListItem'])


    def backwards(self, orm):
        # Deleting model 'GeneList'
        db.delete_table('gene_lists_genelist')

        # Deleting model 'GeneListItem'
        db.delete_table('gene_lists_genelistitem')


    models = {
        'gene_lists.genelist': {
            'Meta': {'object_name': 'GeneList'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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