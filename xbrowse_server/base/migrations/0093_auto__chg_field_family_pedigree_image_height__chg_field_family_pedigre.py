# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Family.pedigree_image_height'
        db.alter_column(u'base_family', 'pedigree_image_height', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Family.pedigree_image_width'
        db.alter_column(u'base_family', 'pedigree_image_width', self.gf('django.db.models.fields.IntegerField')(null=True))

    def backwards(self, orm):

        # Changing field 'Family.pedigree_image_height'
        db.alter_column(u'base_family', 'pedigree_image_height', self.gf('django.db.models.fields.IntegerField')())

        # Changing field 'Family.pedigree_image_width'
        db.alter_column(u'base_family', 'pedigree_image_width', self.gf('django.db.models.fields.IntegerField')())

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'base.causalvariant': {
            'Meta': {'object_name': 'CausalVariant'},
            'alt': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ref': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'variant_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10'}),
            'xpos': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'})
        },
        u'base.cohort': {
            'Meta': {'object_name': 'Cohort'},
            'cohort_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individuals': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.Individual']", 'symmetrical': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'variant_stats_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        u'base.diseasegenelist': {
            'Meta': {'object_name': 'DiseaseGeneList'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_admins': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['base.UserProfile']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        u'base.family': {
            'Meta': {'object_name': 'Family'},
            'about_family_content': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'after_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'analysis_status': ('django.db.models.fields.CharField', [], {'default': "'I'", 'max_length': '1'}),
            'before_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'causal_inheritance_mode': ('django.db.models.fields.CharField', [], {'default': "'unknown'", 'max_length': '20'}),
            'family_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'has_after_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_before_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pedigree_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'pedigree_image_height': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'pedigree_image_width': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'relatedness_matrix_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500', 'blank': 'True'}),
            'variant_stats_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        u'base.familygroup': {
            'Meta': {'object_name': 'FamilyGroup'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'families': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.Family']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100'})
        },
        u'base.familyimageslide': {
            'Meta': {'object_name': 'FamilyImageSlide'},
            'caption': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '300', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.FloatField', [], {'default': '0.0'})
        },
        u'base.familysearchflag': {
            'Meta': {'object_name': 'FamilySearchFlag'},
            'alt': ('django.db.models.fields.TextField', [], {}),
            'date_saved': ('django.db.models.fields.DateTimeField', [], {}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'flag_type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'ref': ('django.db.models.fields.TextField', [], {}),
            'search_spec_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'suggested_inheritance': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'xpos': ('django.db.models.fields.BigIntegerField', [], {})
        },
        u'base.individual': {
            'Meta': {'object_name': 'Individual'},
            'affected': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'bam_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['datasets.BAMFile']", 'null': 'True', 'blank': 'True'}),
            'coverage_file': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'exome_depth_file': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'maternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'other_notes': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'paternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'vcf_files': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['base.VCFFile']", 'null': 'True', 'blank': 'True'}),
            'vcf_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'})
        },
        u'base.individualphenotype': {
            'Meta': {'object_name': 'IndividualPhenotype'},
            'boolean_val': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'float_val': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individual': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Individual']"}),
            'phenotype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.ProjectPhenotype']"})
        },
        u'base.project': {
            'Meta': {'object_name': 'Project'},
            'collaborators': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['auth.User']", 'null': 'True', 'through': u"orm['base.ProjectCollaborator']", 'blank': 'True'}),
            'default_control_cohort': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'gene_lists': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gene_lists.GeneList']", 'through': u"orm['base.ProjectGeneList']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_reference_populations': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['base.ReferencePopulation']", 'null': 'True', 'blank': 'True'}),
            'project_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'unique': 'True', 'max_length': '140', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        u'base.projectcollaborator': {
            'Meta': {'object_name': 'ProjectCollaborator'},
            'collaborator_type': ('django.db.models.fields.CharField', [], {'default': "'collaborator'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'base.projectgenelist': {
            'Meta': {'object_name': 'ProjectGeneList'},
            'gene_list': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gene_lists.GeneList']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"})
        },
        u'base.projectphenotype': {
            'Meta': {'object_name': 'ProjectPhenotype'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'datatype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "'pheno'", 'max_length': '140'})
        },
        u'base.projecttag': {
            'Meta': {'object_name': 'ProjectTag'},
            'color': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"}),
            'tag': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '300'})
        },
        u'base.referencepopulation': {
            'Meta': {'object_name': 'ReferencePopulation'},
            'file_path': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500'}),
            'file_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '50'})
        },
        u'base.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'set_password_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'base.variantnote': {
            'Meta': {'object_name': 'VariantNote'},
            'alt': ('django.db.models.fields.TextField', [], {}),
            'date_saved': ('django.db.models.fields.DateTimeField', [], {}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individual': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Individual']", 'null': 'True', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Project']"}),
            'ref': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'xpos': ('django.db.models.fields.BigIntegerField', [], {})
        },
        u'base.varianttag': {
            'Meta': {'object_name': 'VariantTag'},
            'alt': ('django.db.models.fields.TextField', [], {}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Family']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_tag': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.ProjectTag']"}),
            'ref': ('django.db.models.fields.TextField', [], {}),
            'xpos': ('django.db.models.fields.BigIntegerField', [], {})
        },
        u'base.vcffile': {
            'Meta': {'object_name': 'VCFFile'},
            'file_path': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'needs_reannotate': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'datasets.bamfile': {
            'Meta': {'object_name': 'BAMFile'},
            'file_path': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'network_url': ('django.db.models.fields.TextField', [], {}),
            'storage_mode': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'gene_lists.genelist': {
            'Meta': {'object_name': 'GeneList'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'})
        }
    }

    complete_apps = ['base']