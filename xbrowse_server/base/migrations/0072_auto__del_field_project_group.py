# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing M2M table for field groups on 'UserProfile'
        db.delete_table(db.shorten_name('base_userprofile_groups'))

        # Deleting field 'Project.group'
        db.delete_column('base_project', 'group_id')


    def backwards(self, orm):
        # Adding M2M table for field groups on 'UserProfile'
        m2m_table_name = db.shorten_name('base_userprofile_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userprofile', models.ForeignKey(orm['base.userprofile'], null=False)),
            ('usergroup', models.ForeignKey(orm['base.usergroup'], null=False))
        ))
        db.create_unique(m2m_table_name, ['userprofile_id', 'usergroup_id'])

        # Adding field 'Project.group'
        db.add_column('base_project', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.UserGroup'], null=True, blank=True),
                      keep_default=False)


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
        'base.cohort': {
            'Meta': {'object_name': 'Cohort'},
            '_needs_reload': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cohort_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individuals': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['base.Individual']", 'symmetrical': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'variant_stats_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
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
            '_needs_reload': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'about_family_content': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'after_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'analysis_status': ('django.db.models.fields.CharField', [], {'default': "'I'", 'max_length': '1'}),
            'before_load_qc_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'coll_name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'has_after_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_before_load_qc_error': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_cohort': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'pedigree_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'pedigree_image_height': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'pedigree_image_width': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'relatedness_matrix_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'variant_stats_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        'base.familygroup': {
            'Meta': {'object_name': 'FamilyGroup'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'families': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['base.Family']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100'})
        },
        'base.familysearchflag': {
            'Meta': {'object_name': 'FamilySearchFlag'},
            'alt': ('django.db.models.fields.TextField', [], {}),
            'date_saved': ('django.db.models.fields.DateTimeField', [], {}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'flag_type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'ref': ('django.db.models.fields.TextField', [], {}),
            'search_spec_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'suggested_inheritance': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'xpos': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'base.individual': {
            'Meta': {'object_name': 'Individual'},
            'affected': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'coverage_file': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Family']", 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indiv_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'maternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'other_notes': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'paternal_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']", 'null': 'True', 'blank': 'True'}),
            'vcf_files': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['base.VCFFile']", 'null': 'True', 'blank': 'True'})
        },
        'base.individualphenotype': {
            'Meta': {'object_name': 'IndividualPhenotype'},
            'boolean_val': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'float_val': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individual': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Individual']"}),
            'phenotype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.ProjectPhenotype']"})
        },
        'base.individualphenotypetag': {
            'Meta': {'object_name': 'IndividualPhenotypeTag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'individual': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Individual']"}),
            'phenotype_slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'base.project': {
            'Meta': {'object_name': 'Project'},
            'date_loaded': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 20, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'gene_lists': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['gene_lists.GeneList']", 'through': "orm['base.ProjectGeneList']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_reference_populations': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['base.ReferencePopulation']", 'null': 'True', 'blank': 'True'}),
            'project_id': ('django.db.models.fields.SlugField', [], {'default': "''", 'unique': 'True', 'max_length': '140', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'})
        },
        'base.projectgenelist': {
            'Meta': {'object_name': 'ProjectGeneList'},
            'gene_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['gene_lists.GeneList']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']"})
        },
        'base.projectphenotype': {
            'Meta': {'object_name': 'ProjectPhenotype'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'datatype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.Project']"})
        },
        'base.referencepopulation': {
            'Meta': {'object_name': 'ReferencePopulation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '50'})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projects_can_admin': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'project_admins'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['base.Project']"}),
            'projects_can_edit': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'can_edit_profiles'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['base.Project']"}),
            'projects_can_view': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'can_view_profiles'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['base.Project']"}),
            'set_password_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'base.vcffile': {
            'Meta': {'object_name': 'VCFFile'},
            'file_path': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'needs_reannotate': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'gene_lists.genelist': {
            'Meta': {'object_name': 'GeneList'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '40'})
        }
    }

    complete_apps = ['base']