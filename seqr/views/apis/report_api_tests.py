from django.urls.base import reverse
from django.utils.dateparse import parse_datetime
import json
import mock
import pytz
import responses
from settings import AIRTABLE_URL

from seqr.models import Project, SavedVariant
from seqr.views.apis.report_api import seqr_stats, get_category_projects, discovery_sheet, anvil_export, gregor_export
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, AirtableTest


PROJECT_GUID = 'R0001_1kg'
NON_PROJECT_GUID ='NON_GUID'
PROJECT_EMPTY_GUID = 'R0002_empty'
COMPOUND_HET_PROJECT_GUID = 'R0003_test'
NO_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'

EXPECTED_DISCOVERY_SHEET_ROW = \
    {'project_guid': 'R0001_1kg', 'pubmed_ids': '34415322; 33665635', 'posted_publicly': '',
     'solved': 'TIER 1 GENE', 'head_or_neck': 'N', 'analysis_complete_status': 'complete',
     'cardiovascular_system': 'N', 'n_kindreds_overlapping_sv_similar_phenotype': '2',
     'biochemical_function': 'Y', 'omim_number_post_discovery': '615120,615123',
     'genome_wide_linkage': 'NA 2', 'metabolism_homeostasis': 'N', 'growth': 'N',
     't0': '2017-02-05T06:42:55.397Z', 'months_since_t0': 38, 'sample_source': 'CMG',
     'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
     'expected_inheritance_model': 'Autosomal recessive inheritance',
     'extras_variant_tag_list': ['21-3343353-GAGA-G  RP11  tier 1 - novel gene and phenotype'],
     'protein_interaction': 'N', 'n_kindreds': '1', 'num_individuals_sequenced': 3,
     'musculature': 'Y', 'sequencing_approach': 'WES', 'neoplasm': 'N',
     'collaborator': '1kg project n\xe5me with uni\xe7\xf8de',
     'actual_inheritance_model': 'de novo', 'novel_mendelian_gene': 'Y',
     'endocrine_system': 'N', 'patient_cells': 'N', 'komp_early_release': 'N',
     'connective_tissue': 'N', 'prenatal_development_or_birth': 'N', 'rescue': 'N',
     'family_guid': 'F000001_1', 'immune_system': 'N',
     'analysis_summary': '*\r\nF\u00e5mily analysis summ\u00e5ry.\r\n*; Some additional follow up',
     'gene_count': 'NA', 'gene_id': 'ENSG00000135953', 'abdomen': 'N', 'limbs': 'N',
     'blood': 'N', 'phenotype_class': 'KNOWN', 'submitted_to_mme': 'Y',
     'n_unrelated_kindreds_with_causal_variants_in_gene': '3',
     'row_id': 'F000001_1ENSG00000135953', 'eye_defects': 'N', 'omim_number_initial': '12345',
     'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'Y', 'ear_defects': 'N',
     'thoracic_cavity': 'N', 'non_patient_cell_model': 'N',
     't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped_1.png',
     'family_id': '1', 'genitourinary_system': 'N', 'coded_phenotype': 'myopathy',
     'animal_model': 'N', 'non_human_cell_culture_model': 'N', 'expression': 'N',
     'gene_name': 'RP11', 'breast': 'N'}

EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW = {
    'project_guid': 'R0003_test', 'pubmed_ids': '', 'posted_publicly': '', 'solved': 'TIER 1 GENE', 'head_or_neck': 'N',
    'analysis_complete_status': 'complete', 'cardiovascular_system': 'Y',
    'n_kindreds_overlapping_sv_similar_phenotype': 'NA', 'biochemical_function': 'N', 'omim_number_post_discovery': 'NA',
    'genome_wide_linkage': 'NA', 'metabolism_homeostasis': 'N', 'growth': 'N', 't0': '2017-02-05T06:42:55.397Z',
    'months_since_t0': 38, 'sample_source': 'CMG', 'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
    'expected_inheritance_model': 'multiple', 'num_individuals_sequenced': 2, 'sequencing_approach': 'REAN',
    'extras_variant_tag_list': ['1-248367227-TC-T  OR4G11P  tier 1 - novel gene and phenotype',
        'prefix_19107_DEL  OR4G11P  tier 1 - novel gene and phenotype'], 'protein_interaction': 'N', 'n_kindreds': '1',
    'neoplasm': 'N', 'collaborator': 'Test Reprocessed Project', 'actual_inheritance_model': 'AR-comphet',
    'novel_mendelian_gene': 'Y', 'endocrine_system': 'N', 'komp_early_release': 'N', 'connective_tissue': 'N',
    'prenatal_development_or_birth': 'N', 'rescue': 'N', 'family_guid': 'F000012_12', 'immune_system': 'N',
    'analysis_summary': '', 'gene_count': 'NA', 'gene_id': 'ENSG00000240361', 'abdomen': 'N', 'limbs': 'N',
    'phenotype_class': 'New', 'submitted_to_mme': 'Y', 'n_unrelated_kindreds_with_causal_variants_in_gene': '1',
    'blood': 'N',  'row_id': 'F000012_12ENSG00000240361', 'eye_defects': 'N', 'omim_number_initial': 'NA',
    'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'N', 'ear_defects': 'N', 'thoracic_cavity': 'N',
    'non_patient_cell_model': 'N', 't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '',
    'family_id': '12', 'genitourinary_system': 'N', 'coded_phenotype': '', 'animal_model': 'N', 'expression': 'N',
    'non_human_cell_culture_model': 'N', 'gene_name': 'OR4G11P', 'breast': 'N', 'musculature': 'N', 'patient_cells': 'N',}

AIRTABLE_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "VCGS_FAM203_621_D1",
        "CollaboratorSampleID": "NA19675",
        "Collaborator": ["recW24C2CJW5lT64K"],
        "dbgap_study_id": "dbgap_stady_id_1",
        "dbgap_subject_id": "dbgap_subject_id_1",
        "dbgap_sample_id": "SM-A4GQ4",
        "SequencingProduct": [
          "Mendelian Rare Disease Exome"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-09-09T19:21:12.000Z"
    },
    {
      "id": "rec2Nkg10N1KssPc3",
      "fields": {
        "SeqrCollaboratorSampleID": "HG00731",
        "CollaboratorSampleID": "NA20885",
        "Collaborator": ["reca4hcBnbA2cnZf9"],
        "dbgap_study_id": "dbgap_stady_id_2",
        "dbgap_subject_id": "dbgap_subject_id_2",
        "dbgap_sample_id": "SM-JDBTT",
        "SequencingProduct": [
          "Standard Germline Exome v6 Plus GSA Array"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-07-16T18:23:21.000Z"
    }
]}

AIRTABLE_GREGOR_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "VCGS_FAM203_621_D1",
        "CollaboratorSampleID": "NA19675_1",
        'CollaboratorParticipantID': 'NA19675',
        'SMID': 'SM-AGHT',
        'Recontactable': 'Yes',
      },
    },
    {
      "id": "rec2B67GmXpAkQW8z",
      "fields": {
        'SeqrCollaboratorSampleID': 'NA19679',
        'CollaboratorSampleID': 'NA19679',
        'CollaboratorParticipantID': 'NA19679',
        'SMID': 'SM-N1P91',
        'Recontactable': 'Yes',
      },
    },
    {
      "id": "rec2Nkg10N1KssPc3",
      "fields": {
        "SeqrCollaboratorSampleID": "HG00731",
        "CollaboratorSampleID": "VCGS_FAM203_621_D2",
        'CollaboratorParticipantID': 'VCGS_FAM203_621',
        'SMID': 'SM-JDBTM',
      },
    },
    {
      "id": "rec2Nkg1fKssJc7",
      "fields": {
        'SeqrCollaboratorSampleID': 'NA20888',
        'CollaboratorSampleID': 'NA20888',
        'CollaboratorParticipantID': 'NA20888',
        'SMID': 'SM-L5QMP',
        'Recontactable': 'No',
      },
    },
]}

AIRTABLE_GREGOR_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        'CollaboratorParticipantID': 'VCGS_FAM203_621',
        'CollaboratorSampleID_wes': 'VCGS_FAM203_621_D2',
        'SMID_wes': 'SM-JDBTM',
        'seq_library_prep_kit_method_wes': 'Kapa HyperPrep',
        'read_length_wes': '151',
        'experiment_type_wes': 'exome',
        'targeted_regions_method_wes': 'Twist',
        'targeted_region_bed_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed',
        'date_data_generation_wes': '2022-08-15',
        'target_insert_size_wes': '385',
        'sequencing_platform_wes': 'NovaSeq',
        'aligned_dna_short_read_file_wes': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.cram',
        'aligned_dna_short_read_index_file_wes': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.crai',
        'md5sum_wes': '129c28163df082',
        'reference_assembly': 'GRCh38',
        'alignment_software_dna': 'BWA-MEM-2.3',
        'mean_coverage_wgs': '42.4',
        'analysis_details': 'DOI:10.5281/zenodo.4469317',
        'called_variants_dna_short_read_id': 'SX2-3',
        'aligned_dna_short_read_set_id': 'BCM_H7YG5DSX2',
        'called_variants_dna_file': 'gs://fc-fed09429-e563-44a7-aaeb-776c8336ba02/COL_FAM1_1_D1.SV.vcf',
        'caller_software': 'gatk4.1.2',
        'variant_types': 'SNV',
      },
    },
    {
      "id": "rec2B6OGmCVzkQW3s",
      "fields": {
        'CollaboratorParticipantID': 'NA19675',
        'CollaboratorSampleID_wgs': 'NA19675_1',
        'SMID_wgs': 'SM-AGHT-2',
        'experiment_type_wgs': 'genome',
      },
    },
    {
      "id": "rec4B7OGmQpVkQW7z",
      "fields": {
        'CollaboratorParticipantID': 'NA19679',
        'CollaboratorSampleID_rna': 'NA19679',
        'SMID_rna': 'SM-N1P91',
        'seq_library_prep_kit_method_rna': 'Unknown',
        'library_prep_type_rna': 'stranded poly-A pulldown',
        'read_length_rna': '151',
        'experiment_type_rna': 'paired-end',
        'single_or_paired_ends_rna': 'paired-end',
        'date_data_generation_rna': '2023-02-11',
        'sequencing_platform_rna': 'NovaSeq',
        'aligned_rna_short_read_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.cram',
        'aligned_rna_short_read_index_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.crai',
        'md5sum_rna': 'f6490b8ebdf2',
        '5prime3prime_bias_rna': '1.05',
        'gene_annotation_rna': 'GENCODEv26',
        'reference_assembly': 'GRCh38',
        'reference_assembly_uri_rna': 'gs://gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta',
        'alignment_software_rna': 'STARv2.7.10b',
        'alignment_log_file_rna': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Log.final.out',
        'percent_uniquely_aligned_rna': '80.53',
        'percent_multimapped_rna': '17.08',
        'percent_unaligned_rna': '1.71',
        'percent_mRNA': '80.2',
        'percent_rRNA': '5.9',
        'RIN_rna': '8.9818',
        'total_reads_rna': '106,842,386',
        'within_site_batch_name_rna': 'LCSET-26942',
        'estimated_library_size_rna': '19,480,858',
        'variant_types': 'SNV',
      },
    },
    {
      "id": "rec2BFCGmQpAkQ7x",
      "fields": {
        'CollaboratorParticipantID': 'NA20888',
        'CollaboratorSampleID_wes': 'NA20888',
        'CollaboratorSampleID_wgs': 'NA20888_1',
        'SMID_wes': 'SM-L5QMP',
        'SMID_wgs': 'SM-L5QMWP',
        'seq_library_prep_kit_method_wes': 'Kapa HyperPrep',
        'seq_library_prep_kit_method_wgs': 'Kapa HyperPrep w/o amplification',
        'read_length_wes': '151',
        'read_length_wgs': '200',
        'experiment_type_wes': 'exome',
        'experiment_type_wgs': 'genome',
        'targeted_regions_method_wes': 'Twist',
        'targeted_region_bed_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed',
        'date_data_generation_wes': '2022-06-05',
        'date_data_generation_wgs': '2023-03-13',
        'target_insert_size_wes': '380',
        'target_insert_size_wgs': '450',
        'sequencing_platform_wes': 'NovaSeq',
        'sequencing_platform_wgs': 'NovaSeq2',
        'aligned_dna_short_read_file_wes': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.cram',
        'aligned_dna_short_read_index_file_wes': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.crai',
        'aligned_dna_short_read_file_wgs': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.cram',
        'aligned_dna_short_read_index_file_wgs': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.crai',
        'md5sum_wes': 'a6f6308866765ce8',
        'md5sum_wgs': '2aa33e8c32020b1c',
        'reference_assembly': 'GRCh38',
        'alignment_software_dna': 'BWA-MEM-2.3',
        'mean_coverage_wes': '42.8',
        'mean_coverage_wgs': '36.1',
        'analysis_details': '',
        'called_variants_dna_short_read_id': '',
        'aligned_dna_short_read_set_id': 'Broad_NA20888_D1',
        'called_variants_dna_file': '',
        'caller_software': 'NA',
        'variant_types': 'SNV',
      },
    },
]}
EXPECTED_GREGOR_FILES = [
    'participant', 'family', 'phenotype', 'analyte', 'experiment_dna_short_read',
    'aligned_dna_short_read', 'aligned_dna_short_read_set', 'called_variants_dna_short_read',
    'experiment_rna_short_read', 'aligned_rna_short_read', 'experiment', 'genetic_findings',
]

MOCK_DATA_MODEL_URL = 'http://raw.githubusercontent.com/gregor_data_model.json'
MOCK_DATA_MODEL = {
    'name': 'test data model',
    'tables': [
        {
            'table': 'participant',
            'required': True,
            'columns': [
                {'column': 'participant_id', 'required': True, 'data_type': 'string'},
                {'column': 'internal_project_id'},
                {'column': 'gregor_center', 'required': True, 'data_type': 'enumeration', 'enumerations': ['BCM', 'BROAD', 'UW']},
                {'column': 'consent_code', 'required': True, 'data_type': 'enumeration', 'enumerations': ['GRU', 'HMB']},
                {'column': 'recontactable', 'data_type': 'enumeration', 'enumerations': ['Yes', 'No']},
                {'column': 'prior_testing'},
                {'column': 'pmid_id'},
                {'column': 'family_id', 'required': True},
                {'column': 'paternal_id'},
                {'column': 'maternal_id'},
                {'column': 'twin_id'},
                {'column': 'proband_relationship'},
                {'column': 'proband_relationship_detail'},
                {'column': 'sex', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Male', 'Female', 'Unknown']},
                {'column': 'sex_detail'},
                {'column': 'reported_race', 'data_type': 'enumeration', 'enumerations': ['American Indian or Alaska Native', 'Asian', 'Black or African American', 'Native Hawaiian or Other Pacific Islander', 'Middle Eastern or North African', 'White']},
                {'column': 'reported_ethnicity', 'data_type': 'enumeration', 'enumerations': ['Hispanic or Latino', 'Not Hispanic or Latino']},
                {'column': 'ancestry_detail'},
                {'column': 'age_at_last_observation'},
                {'column': 'affected_status', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Affected', 'Unaffected', 'Unknown']},
                {'column': 'phenotype_description'},
                {'column': 'age_at_enrollment'},
                {'column': 'solve_status', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Yes', 'Likely', 'No', 'Partial']},
                {'column': 'missing_variant_case', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Yes', 'No']},
            ],
        },
        {
            'table': 'family',
            'required': True,
            'columns': [
                {'column': 'family_id', 'required': True, 'data_type': 'string'},
                {'column': 'consanguinity', 'required': True, 'data_type': 'enumeration', 'enumerations': ['None suspected', 'Suspected', 'Present', 'Unknown']},
                {'column': 'consanguinity_detail'},
            ]
        },
        {
            'table': 'phenotype',
            'required': True,
            'columns': [
                {'column': 'phenotype_id'},
                {'column': 'participant_id', 'references': '> participant.participant_id', 'required': True, 'data_type': 'string'},
                {'column': 'term_id', 'required': True},
                {'column': 'presence', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Present', 'Absent', 'Unknown']},
                {'column': 'ontology', 'required': True, 'data_type': 'enumeration', 'enumerations': ['HPO', 'MONDO']},
                {'column': 'additional_details'},
                {'column': 'onset_age_range'},
                {'column': 'additional_modifiers'},
            ]
        },
        {
            'table': 'analyte',
            'required': True,
            'columns': [
                {'column': 'analyte_id', 'required': True, 'data_type': 'string'},
                {'column': 'participant_id', 'required': True, 'data_type': 'string'},
                {'column': 'analyte_type', 'data_type': 'enumeration', 'enumerations': ['DNA', 'RNA', 'cDNA', 'blood plasma', 'frozen whole blood', 'high molecular weight DNA', 'urine']},
                {'column': 'analyte_processing_details'},
                {'column': 'primary_biosample'},
                {'column': 'primary_biosample_id'},
                {'column': 'primary_biosample_details'},
                {'column': 'tissue_affected_status', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Yes', 'No']},
            ]
        },
        {
            'table': 'experiment',
            'columns': [
                {'column': 'experiment_id', 'required': True, 'data_type': 'string'},
                {'column': 'table_name', 'required': True, 'data_type': 'enumeration', 'enumerations': ['experiment_dna_short_read', 'experiment_rna_short_read']},
                {'column': 'id_in_table', 'required': True},
                {'column': 'participant_id', 'required': True},
            ]
        },
        {
            'table': 'experiment_dna_short_read',
            'required': 'CONDITIONAL (aligned_dna_short_read, aligned_dna_short_read_set, called_variants_dna_short_read)',
            'columns': [
                {'column': 'experiment_dna_short_read_id', 'required': True},
                {'column': 'analyte_id', 'required': True},
                {'column': 'experiment_sample_id', 'required': True},
                {'column': 'seq_library_prep_kit_method'},
                {'column': 'read_length', 'data_type': 'integer'},
                {'column': 'experiment_type', 'required': True, 'data_type': 'enumeration', 'enumerations': ['targeted', 'genome', 'exome']},
                {'column': 'targeted_regions_method'},
                {'column': 'targeted_region_bed_file', 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'date_data_generation', 'data_type': 'date'},
                {'column': 'target_insert_size', 'data_type': 'integer'},
                {'column': 'sequencing_platform'},
            ],
        },
        {
            'table': 'aligned_dna_short_read',
            'required': 'CONDITIONAL (aligned_dna_short_read_set, called_variants_dna_short_read)',
            'columns': [
                {'column': 'aligned_dna_short_read_id', 'required': True},
                {'column': 'experiment_dna_short_read_id', 'required': True},
                {'column': 'aligned_dna_short_read_file', 'is_unique': True, 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'aligned_dna_short_read_index_file', 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'md5sum', 'is_unique': True},
                {'column': 'reference_assembly', 'data_type': 'enumeration', 'enumerations': ['GRCh38', 'GRCh37']},
                {'column': 'reference_assembly_uri'},
                {'column': 'reference_assembly_details'},
                {'column': 'mean_coverage', 'data_type': 'float'},
                {'column': 'alignment_software', 'required': True},
                {'column': 'analysis_details', 'data_type': 'string'},
                {'column': 'quality_issues'},
            ],
        },
        {
            'table': 'aligned_dna_short_read_set',
            'required': 'CONDITIONAL (called_variants_dna_short_read)',
            'columns': [
                {'column': 'aligned_dna_short_read_set_id', 'required': True},
                {'column': 'aligned_dna_short_read_id', 'required': True},
            ],
        },
        {
            'table': 'called_variants_dna_short_read',
            'columns': [
                {'column': 'called_variants_dna_short_read_id', 'required': True, 'is_unique': True},
                {'column': 'aligned_dna_short_read_set_id', 'required': True},
                {'column': 'called_variants_dna_file', 'is_unique': True, 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'md5sum', 'required': True, 'is_unique': True},
                {'column': 'caller_software', 'required': True},
                {'column': 'variant_types', 'required': True, 'data_type': 'enumeration', 'enumerations': ['SNV', 'INDEL', 'SV', 'CNV', 'RE','MEI', 'STR']},
                {'column': 'analysis_details'},
            ],
        },
        {
            'table': 'experiment_rna_short_read',
            'required': 'CONDITIONAL (aligned_rna_short_read)',
            'columns': [
                {'column': 'experiment_rna_short_read_id', 'required': True},
                {'column': 'analyte_id', 'required': True},
                {'column': 'experiment_sample_id'},
                {'column': 'seq_library_prep_kit_method'},
                {'column': 'read_length', 'data_type': 'integer'},
                {'column': 'experiment_type'},
                {'column': 'date_data_generation', 'data_type': 'date'},
                {'column': 'sequencing_platform'},
                {'column': 'library_prep_type'},
                {'column': 'single_or_paired_ends'},
                {'column': 'within_site_batch_name'},
                {'column': 'RIN', 'data_type': 'float'},
                {'column': 'estimated_library_size', 'data_type': 'float'},
                {'column': 'total_reads', 'data_type': 'integer'},
                {'column': 'percent_rRNA', 'data_type': 'float'},
                {'column': 'percent_mRNA', 'data_type': 'float'},
                {'column': '5prime3prime_bias', 'data_type': 'float'},
                {'column': 'percent_mtRNA', 'data_type': 'float'},
                {'column': 'percent_Globin', 'data_type': 'float'},
                {'column': 'percent_UMI', 'data_type': 'float'},
                {'column': 'percent_GC', 'data_type': 'float'},
                {'column': 'percent_chrX_Y', 'data_type': 'float'},
            ],
        },
        {
            'table': 'aligned_rna_short_read',
            'columns': [
                {'column': 'aligned_rna_short_read_id', 'required': True},
                {'column': 'experiment_rna_short_read_id', 'required': True},
                {'column': 'aligned_rna_short_read_file', 'is_unique': True, 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'aligned_rna_short_read_index_file', 'data_type': 'string', 'is_bucket_path': True},
                {'column': 'md5sum', 'is_unique': True},
                {'column': 'reference_assembly', 'data_type': 'enumeration', 'enumerations': ['GRCh38', 'GRCh37']},
                {'column': 'reference_assembly_uri'},
                {'column': 'reference_assembly_details'},
                {'column': 'mean_coverage', 'data_type': 'float'},
                {'column': 'gene_annotation', 'required': True},
                {'column': 'gene_annotation_details'},
                {'column': 'alignment_software', 'required': True},
                {'column': 'alignment_log_file', 'required': True},
                {'column': 'alignment_postprocessing'},
                {'column': 'percent_uniquely_aligned'},
                {'column': 'percent_multimapped'},
                {'column': 'percent_unaligned'},
                {'column': 'quality_issues'},
            ],
        },
        {
            'table': 'genetic_findings',
            'columns': [
                {'column': 'genetic_findings_id', 'required': True},
                {'column': 'participant_id', 'required': True},
                {'column': 'experiment_id'},
                {'column': 'variant_type', 'required': True, 'data_type': 'enumeration', 'enumerations': ['SNV/INDEL', 'SV', 'CNV', 'RE', 'MEI']},
                {'column': 'variant_reference_assembly', 'required': True, 'data_type': 'enumeration', 'enumerations': ['GRCh37', 'GRCh38']},
                {'column': 'chrom', 'required': True},
                {'column': 'pos', 'required': True, 'data_type': 'integer'},
                {'column': 'ref','required': True},
                {'column': 'alt', 'required': True},
                {'column': 'ClinGen_allele_ID'},
                {'column': 'gene', 'required': True},
                {'column': 'transcript'},
                {'column': 'hgvsc'},
                {'column': 'hgvsp'},
                {'column': 'zygosity', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Heterozygous', 'Homozygous', 'Hemizygous', 'Heteroplasmy', 'Homoplasmy', 'Mosaic']},
                {'column': 'allele_balance_or_heteroplasmy_percentage', 'data_type': 'float'},
                {'column': 'variant_inheritance', 'data_type': 'enumeration', 'enumerations': ['de novo', 'maternal', 'paternal', 'biparental', 'nonmaternal', 'nonpaternal', 'unknown']},
                {'column': 'linked_variant'},
                {'column': 'linked_variant_phase'},
                {'column': 'gene_known_for_phenotype', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Known', 'Candidate']},
                {'column': 'known_condition_name'},
                {'column': 'condition_id'},
                {'column': 'condition_inheritance', 'data_type': 'enumeration', 'multi_value_delimiter': '|', 'enumerations': ['Autosomal recessive', 'Autosomal dominant', 'X-linked', 'Mitochondrial', 'Y-linked', 'Contiguous gene syndrome', 'Somatic mosaicism', 'Digenic', 'Other', 'Unknown']},
                {'column': 'phenotype_contribution', 'data_type': 'enumeration', 'enumerations': ['Partial', 'Full', 'Uncertain']},
                {'column': 'partial_contribution_explained'},
                {'column': 'additional_family_members_with_variant'},
                {'column': 'method_of_discovery', 'data_type': 'enumeration', 'multi_value_delimiter': '|', 'enumerations': ['SR-ES', 'SR-GS', 'LR-GS', 'SNP array']},
                {'column': 'notes'}
            ]
        },
    ]
}
MOCK_DATA_MODEL_RESPONSE = json.dumps(MOCK_DATA_MODEL, indent=2).replace('"references"', '//"references"')

INVALID_MODEL_TABLES = {
    'participant': {
        'internal_project_id': {'data_type': 'reference'},
        'prior_testing': {'data_type': 'enumeration'},
        'proband_relationship': {'required': True},
        'reported_race': {'enumerations': ['Asian', 'White', 'Black']},
        'age_at_enrollment': {'data_type': 'date'}
    },
    'aligned_dna_short_read': {
        'analysis_details': {'is_bucket_path': True},
        'reference_assembly': {'data_type': 'integer'},
        'mean_coverage': {'required': True},
        'alignment_software': {'is_unique': True},
    },
    'aligned_dna_short_read_set': {},
    'experiment_rna_short_read': {'date_data_generation': {'data_type': 'float'}},
    'genetic_findings': {'experiment_id': {'required': True}},
}
INVALID_TABLES = [
    {**t, 'columns': [{**c, **(INVALID_MODEL_TABLES[t['table']].get(c['column'], {}))} for c in t['columns']]}
    for t in MOCK_DATA_MODEL['tables'] if t['table'] in INVALID_MODEL_TABLES
]
INVALID_TABLES[0]['columns'] = [c for c in INVALID_TABLES[0]['columns'] if c['column'] not in {
    'pmid_id', 'age_at_last_observation', 'ancestry_detail', 'missing_variant_case',
}]
MOCK_INVALID_DATA_MODEL = {
    'tables': [
        {
            'table': 'subject',
            'required': True,
            'columns': [{'column': 'subject_id', 'required': True}],
        },
        {
            'table': 'dna_read_data',
            'columns': [{'column': 'analyte_id', 'required': True}],
        },
        {
            'table': 'dna_read_data_set',
            'required': 'CONDITIONAL (aligned_dna_short_read_set, dna_read_data)',
            'columns': [{'column': 'analyte_id', 'required': True}],
        },
    ] + INVALID_TABLES
}


class ReportAPITest(AirtableTest):

    def _get_zip_files(self, mock_zip, filenames):
        mock_write_zip = mock_zip.return_value.__enter__.return_value.writestr
        self.assertEqual(mock_write_zip.call_count, len(filenames))
        mock_write_zip.assert_has_calls([mock.call(file, mock.ANY) for file in filenames])

        return (
            [row.split('\t') for row in mock_write_zip.call_args_list[i][0][1].split('\n') if row]
            for i in range(len(filenames))
        )

    def test_seqr_stats(self):
        no_access_project = Project.objects.get(id=2)
        no_access_project.workspace_namespace = None
        no_access_project.save()

        url = reverse(seqr_stats)
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'projectsCount', 'individualsCount', 'familiesCount', 'sampleCountsByType'})
        self.assertDictEqual(response_json['projectsCount'], self.STATS_DATA['projectsCount'])
        self.assertDictEqual(response_json['individualsCount'], self.STATS_DATA['individualsCount'])
        self.assertDictEqual(response_json['familiesCount'], self.STATS_DATA['familiesCount'])
        self.assertDictEqual(response_json['sampleCountsByType'], self.STATS_DATA['sampleCountsByType'])

        self.check_no_analyst_no_access(url)

    def test_get_category_projects(self):
        url = reverse(get_category_projects, args=['GREGoR'])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['projectGuids'])
        self.assertSetEqual(set(response_json['projectGuids']), {PROJECT_GUID, COMPOUND_HET_PROJECT_GUID})

        self.check_no_analyst_no_access(url)

    @mock.patch('seqr.views.apis.report_api.timezone')
    def test_discovery_sheet(self, mock_timezone):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        self.check_analyst_login(non_project_url)

        mock_timezone.now.return_value = pytz.timezone("US/Eastern").localize(parse_datetime("2020-04-27 20:16:01"), is_dst=None)
        response = self.client.get(non_project_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid project {}'.format(NON_PROJECT_GUID))
        response_json = response.json()
        self.assertEqual(response_json['error'], 'Invalid project {}'.format(NON_PROJECT_GUID))

        unauthorized_project_url = reverse(discovery_sheet, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)

        empty_project_url = reverse(discovery_sheet, args=[PROJECT_EMPTY_GUID])

        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['rows'], [])
        self.assertListEqual(response_json['errors'], ["No data loaded for project: Empty Project"])

        url = reverse(discovery_sheet, args=[PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], ['No data loaded for family: 9. Skipping...', 'No data loaded for family: no_individuals. Skipping...'])
        self.assertEqual(len(response_json['rows']), 10)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_ROW, response_json['rows'])

        # test compound het reporting
        url = reverse(discovery_sheet, args=[COMPOUND_HET_PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], [
            'HPO category field not set for some HPO terms in 11', 'HPO category field not set for some HPO terms in 12',
        ])
        self.assertEqual(len(response_json['rows']), 2)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW, response_json['rows'])

        self.check_no_analyst_no_access(url)

    @mock.patch('seqr.views.utils.export_utils.zipfile.ZipFile')
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @responses.activate
    def test_anvil_export(self, mock_google_authenticated,  mock_zip):
        mock_google_authenticated.return_value = False
        url = reverse(anvil_export, args=[PROJECT_GUID])
        self.check_analyst_login(url)

        no_analyst_project_url = reverse(anvil_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(no_analyst_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')
        mock_google_authenticated.return_value = True

        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), json=AIRTABLE_SAMPLE_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('content-disposition'),
            'attachment; filename="1kg project nme with unide_AnVIL_Metadata.zip"'
        )

        subject_file, sample_file, family_file, discovery_file = self._get_zip_files(mock_zip, [
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Subject.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Sample.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Family.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery.tsv',
        ])

        self.assertEqual(subject_file[0], [
            'entity:subject_id', '01-subject_id', '02-prior_testing', '03-project_id', '04-pmid_id',
            '05-dbgap_study_id', '06-dbgap_subject_id', '07-multiple_datasets',
            '08-family_id', '09-paternal_id', '10-maternal_id', '11-twin_id', '12-proband_relationship', '13-sex',
            '14-ancestry', '15-ancestry_detail', '16-age_at_last_observation', '17-phenotype_group', '18-disease_id',
            '19-disease_description', '20-affected_status', '21-congenital_status', '22-age_of_onset', '23-hpo_present',
            '24-hpo_absent', '25-phenotype_description', '26-solve_state'])
        self.assertIn([
            'NA19675_1', 'NA19675_1', '-', u'1kg project nme with unide', '34415322', 'dbgap_stady_id_1',
            'dbgap_subject_id_1', 'No', '1', 'NA19678', 'NA19679', '-', 'Self', 'Male', 'Other', 'Middle Eastern', '-',
            '-', 'OMIM:615120;OMIM:615123', 'Myasthenic syndrome; congenital; 8; with pre- and postsynaptic defects;',
            'Affected', 'Adult onset', '-', 'HP:0001631|HP:0002011|HP:0001636', 'HP:0011675|HP:0001674|HP:0001508',
            'myopathy', 'Tier 1'], subject_file)

        self.assertEqual(sample_file[0], [
            'entity:sample_id', '01-subject_id', '02-sample_id', '03-dbgap_sample_id', '04-sequencing_center',
            '05-sample_source', '06-tissue_affected_status',])
        self.assertIn(
            ['NA19675_1', 'NA19675_1', 'NA19675', 'SM-A4GQ4', 'Broad', '-', '-'],
            sample_file,
        )

        self.assertEqual(family_file[0], [
            'entity:family_id', '01-family_id', '02-consanguinity', '03-consanguinity_detail', '04-pedigree_image',
            '05-pedigree_detail', '06-family_history', '07-family_onset'])
        self.assertIn([
            '1', '1', 'Present', '-', '-', '-', '-', '-',
        ], family_file)

        self.assertEqual(len(discovery_file), 6)
        self.assertEqual(discovery_file[0], [
            'entity:discovery_id', '01-subject_id', '02-sample_id', '03-Gene', '04-Gene_Class',
            '05-inheritance_description', '06-Zygosity', '07-variant_genome_build', '08-Chrom', '09-Pos',
            '10-Ref', '11-Alt', '12-hgvsc', '13-hgvsp', '14-Transcript', '15-sv_name', '16-sv_type',
            '17-significance', '18-discovery_notes'])
        self.assertIn([
            '1_248367227_HG00731', 'HG00731', 'HG00731', 'RP11', 'Known', 'Autosomal recessive (homozygous)',
            'Homozygous', 'GRCh37', '1', '248367227', 'TC', 'T', '-', '-', '-', '-', '-', '-', '-'], discovery_file)
        self.assertIn([
            '21_3343353_NA19675_1', 'NA19675_1', 'NA19675', 'RP11', 'Tier 1 - Candidate', 'de novo',
            'Heterozygous', 'GRCh37', '21', '3343353', 'GAGA', 'G', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-', '-'], discovery_file)
        self.assertIn([
            '19_1912633_HG00733', 'HG00733', 'HG00733', 'OR4G11P', 'Known', 'Unknown / Other', 'Heterozygous', 'GRCh38.p12', '19',
            '1912633', 'G', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-GC-TT '
            '(c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)
        self.assertIn([
            '19_1912634_HG00733', 'HG00733', 'HG00733', 'OR4G11P', 'Known', 'Unknown / Other', 'Heterozygous', 'GRCh38.p12', '19',
            '1912634', 'C', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-GC-TT (c.586_587delinsTT, '
            'p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)

        added_perm = self.add_analyst_project(4)
        if added_perm:
            response = self.client.get(no_analyst_project_url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['errors'], ['Discovery variant 12-48367227-TC-T in family 14 has no associated gene'])

        self.check_no_analyst_no_access(url)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch('seqr.views.apis.report_api.GREGOR_DATA_MODEL_URL', MOCK_DATA_MODEL_URL)
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @mock.patch('seqr.views.apis.report_api.datetime')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @responses.activate
    def test_gregor_export(self, mock_subprocess, mock_temp_dir, mock_open, mock_datetime, mock_google_authenticated):
        mock_datetime.now.return_value.year = 2020
        mock_google_authenticated.return_value = False
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        mock_subprocess.return_value.wait.return_value = 1

        responses.add(
            responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), json=AIRTABLE_GREGOR_SAMPLE_RECORDS,
            status=200)
        responses.add(
            responses.GET, '{}/app3Y97xtbbaOopVR/GREGoR Data Model'.format(AIRTABLE_URL), json=AIRTABLE_GREGOR_RECORDS,
            status=200)
        responses.add(responses.GET, MOCK_DATA_MODEL_URL, status=404)

        url = reverse(gregor_export)
        self.check_analyst_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Missing required field(s): consentCode, deliveryPath'])

        body = {'consentCode': 'HMB', 'deliveryPath': '/test/file'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Delivery Path must be a valid google bucket path (starts with gs://)'])

        body['deliveryPath'] = 'gs://anvil-upload'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Invalid Delivery Path: folder not found'])

        mock_subprocess.return_value.wait.return_value = 0
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        mock_google_authenticated.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Unable to load data model: 404 Client Error: Not Found for url: http://raw.githubusercontent.com/gregor_data_model.json',
        ])

        responses.add(responses.GET, MOCK_DATA_MODEL_URL, json=MOCK_INVALID_DATA_MODEL, status=200)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)

        recommended_warnings = [
            'The following entries are missing recommended "recontactable" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881',
            'The following entries are missing recommended "reported_race" in the "participant" table: Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "phenotype_description" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "age_at_enrollment" in the "participant" table: Broad_HG00731, Broad_NA20870, Broad_NA20872, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "known_condition_name" in the "genetic_findings" table: Broad_HG00731',
        ]
        self.assertListEqual(response.json()['warnings'], [
            'The following columns are specified as "enumeration" in the "participant" data model but are missing the allowed values definition: prior_testing',
            'The following columns are included in the "participant" data model but have an unsupported data type: internal_project_id (reference)',
            'The following columns are computed for the "participant" table but are missing from the data model: age_at_last_observation, ancestry_detail, missing_variant_case, pmid_id',
        ] + recommended_warnings)
        self.assertListEqual(response.json()['errors'], [
            f'No data model found for "{file}" table' for file in reversed(EXPECTED_GREGOR_FILES) if file not in INVALID_MODEL_TABLES
        ] + [
            'The following tables are required in the data model but absent from the reports: subject, dna_read_data_set',
        ] + [
            'The following entries are missing required "proband_relationship" in the "participant" table: Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries have invalid values for "reported_race" in the "participant" table. Allowed values: Asian, White, Black. Invalid values: Broad_NA19675_1 (Middle Eastern or North African)',
            'The following entries have invalid values for "age_at_enrollment" in the "participant" table. Allowed values have data type date. Invalid values: Broad_NA19675_1 (18)',
            'The following entries have invalid values for "reference_assembly" (from Airtable) in the "aligned_dna_short_read" table. Allowed values have data type integer. Invalid values: NA20888 (GRCh38), VCGS_FAM203_621_D2 (GRCh38)',
            'The following entries are missing required "mean_coverage" (from Airtable) in the "aligned_dna_short_read" table: VCGS_FAM203_621_D2',
            'The following entries have non-unique values for "alignment_software" (from Airtable) in the "aligned_dna_short_read" table: BWA-MEM-2.3 (NA20888, VCGS_FAM203_621_D2)',
            'The following entries have invalid values for "analysis_details" (from Airtable) in the "aligned_dna_short_read" table. Allowed values are a google bucket path starting with gs://. Invalid values: VCGS_FAM203_621_D2 (DOI:10.5281/zenodo.4469317)',
            'The following entries have invalid values for "date_data_generation" (from Airtable) in the "experiment_rna_short_read" table. Allowed values have data type float. Invalid values: NA19679 (2023-02-11)',
            'The following entries are missing required "experiment_id" (from Airtable) in the "genetic_findings" table: Broad_NA19675_1',
        ])

        responses.calls.reset()
        mock_subprocess.reset_mock()
        responses.add(responses.GET, MOCK_DATA_MODEL_URL, body=MOCK_DATA_MODEL_RESPONSE, status=200)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        expected_response = {
            'info': ['Successfully validated and uploaded Gregor Report for 9 families'],
            'warnings': recommended_warnings,
        }
        self.assertDictEqual(response.json(), expected_response)
        self._assert_expected_gregor_files(mock_open)
        self._test_expected_gregor_airtable_calls()

        # test gsutil commands
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://anvil-upload', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
            mock.call('gsutil mv /mock/tmp/* gs://anvil-upload', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ])

        # Test multiple project with shared sample IDs
        project = Project.objects.get(id=3)
        project.consent_code = 'H'
        project.save()

        # Currently not reporting SV discoveries, so modify fixture data to report comp het pair
        # Remove this once we are reporting SVs
        variant = SavedVariant.objects.get(id=7)
        variant.ref = 'A'
        variant.alt = 'G'
        variant.saved_variant_json['genotypes']['I000017_na20889']['numAlt'] = 1
        variant.saved_variant_json['transcripts'] = {'ENSG00000240361': []}
        variant.save()

        responses.calls.reset()
        responses.add(responses.GET, 'https://monarchinitiative.org/v3/api/entity/MONDO:0008788', status=200, json={
            'id': 'MONDO:0008788',
            'category': 'biolink:Disease',
            'name': 'IRIDA syndrome',
            'inheritance': {
                'id': 'HP:0000006',
                'category': 'biolink:PhenotypicFeature',
                'name': 'Autosomal dominant inheritance (HPO)',
            },
        })
        mock_open.reset_mock()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        expected_response['info'][0] = expected_response['info'][0].replace('9', '10')
        expected_response['warnings'][0] = expected_response['warnings'][0] + ', Broad_NA20885, Broad_NA20889'
        expected_response['warnings'][2] = expected_response['warnings'][2].replace('Broad_NA20888', 'Broad_NA20885, Broad_NA20888, Broad_NA20889')
        expected_response['warnings'][3] = expected_response['warnings'][3].replace('Broad_NA20888', 'Broad_NA20885, Broad_NA20888, Broad_NA20889')
        self.assertDictEqual(response.json(), expected_response)
        self._assert_expected_gregor_files(mock_open, has_second_project=True)
        self._test_expected_gregor_airtable_calls(additional_samples=['NA20885', 'NA20889'], additional_mondo_ids=['0008788'])

        self.check_no_analyst_no_access(url)

    def _assert_expected_gregor_files(self, mock_open, has_second_project=False):
        self.assertListEqual(
            mock_open.call_args_list, [mock.call(f'/mock/tmp/{file}.tsv', 'w') for file in EXPECTED_GREGOR_FILES])
        files = [
            [row.split('\t') for row in write_call.args[0].split('\n')]
            for write_call in mock_open.return_value.__enter__.return_value.write.call_args_list
        ]
        participant_file, family_file, phenotype_file, analyte_file, experiment_file, read_file, read_set_file, \
        called_file, experiment_rna_file, aligned_rna_file, experiment_lookup_file, genetic_findings_file = files

        self.assertEqual(len(participant_file), 16 if has_second_project else 14)
        self.assertEqual(participant_file[0], [
            'participant_id', 'internal_project_id', 'gregor_center', 'consent_code', 'recontactable', 'prior_testing',
            'pmid_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id', 'proband_relationship',
            'proband_relationship_detail', 'sex', 'sex_detail', 'reported_race', 'reported_ethnicity', 'ancestry_detail',
            'age_at_last_observation', 'affected_status', 'phenotype_description', 'age_at_enrollment', 'solve_status',
            'missing_variant_case',
        ])
        row = next(r for r in participant_file if r[0] == 'Broad_NA19675_1')
        self.assertListEqual([
            'Broad_NA19675_1', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', 'Yes', 'IKBKAP|CCDC102B|CMA - normal',
            '34415322|33665635', 'Broad_1', 'Broad_NA19678', 'Broad_NA19679', '', 'Self', '', 'Male', '',
            'Middle Eastern or North African', '', '', '21', 'Affected', 'myopathy', '18', 'No', 'No',
        ], row)
        hispanic_row = next(r for r in participant_file if r[0] == 'Broad_HG00731')
        self.assertListEqual([
            'Broad_HG00731', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_2', 'Broad_HG00732',
            'Broad_HG00733', '', 'Self', '', 'Female', '', '', 'Hispanic or Latino', 'Other', '', 'Affected', '', '', 'No', 'No',
        ], hispanic_row)
        solved_row = next(r for r in participant_file if r[0] == 'Broad_NA20876')
        self.assertListEqual([
            'Broad_NA20876', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_7', '0',
            '0', '', '', '', 'Male', '', '', '', '', '', 'Affected', '', '', 'Yes', 'No',
        ], solved_row)
        multi_data_type_row = next(r for r in participant_file if r[0] == 'Broad_NA20888')
        self.assertListEqual([
            'Broad_NA20888', 'Broad_Test Reprocessed Project' if has_second_project else 'Broad_1kg project nme with unide',
            'BROAD', 'HMB', 'No', '', '', 'Broad_12' if has_second_project else 'Broad_8', '0', '0', '', '', '',
            'Male' if has_second_project else 'Female', '', '', '', '', '', 'Affected', '', '', 'No', 'No',
        ], multi_data_type_row)

        self.assertEqual(len(family_file), 11 if has_second_project else 10)
        self.assertEqual(family_file[0], [
            'family_id', 'consanguinity', 'consanguinity_detail',
        ])
        self.assertIn(['Broad_1', 'Present', ''], family_file)
        fam_8_row = ['Broad_8', 'Unknown', '']
        fam_11_row = ['Broad_11', 'None suspected', '']
        if has_second_project:
            self.assertIn(fam_11_row, family_file)
            self.assertNotIn(fam_8_row, family_file)
        else:
            self.assertIn(fam_8_row, family_file)
            self.assertNotIn(fam_11_row, family_file)

        self.assertEqual(len(phenotype_file), 14 if has_second_project else 10)
        self.assertEqual(phenotype_file[0], [
            'phenotype_id', 'participant_id', 'term_id', 'presence', 'ontology', 'additional_details',
            'onset_age_range', 'additional_modifiers',
        ])
        self.assertIn([
            '', 'Broad_NA19675_1', 'HP:0002011', 'Present', 'HPO', '', 'HP:0003593', 'HP:0012825|HP:0003680',
        ], phenotype_file)
        self.assertIn([
            '', 'Broad_NA19675_1', 'HP:0001674', 'Absent', 'HPO', 'originally indicated', '', '',
        ], phenotype_file)

        self.assertEqual(len(analyte_file), 6 if has_second_project else 5)
        self.assertEqual(analyte_file[0], [
            'analyte_id', 'participant_id', 'analyte_type', 'analyte_processing_details', 'primary_biosample',
            'primary_biosample_id', 'primary_biosample_details', 'tissue_affected_status',
        ])
        row = next(r for r in analyte_file if r[1] == 'Broad_NA19675_1')
        self.assertListEqual(
            ['Broad_SM-AGHT', 'Broad_NA19675_1', 'DNA', '', 'UBERON:0003714', '', '', 'No'],
            row)
        self.assertIn(
            ['Broad_SM-L5QMP', 'Broad_NA20888', '', '', '', '', '', 'No'], analyte_file)
        self.assertEqual(
            ['Broad_SM-L5QMWP', 'Broad_NA20888', '', '', '', '', '', 'No'] in analyte_file,
            has_second_project
        )

        num_airtable_rows = 4 if has_second_project else 3
        self.assertEqual(len(experiment_file), num_airtable_rows)
        self.assertEqual(experiment_file[0], [
            'experiment_dna_short_read_id', 'analyte_id', 'experiment_sample_id', 'seq_library_prep_kit_method',
            'read_length', 'experiment_type', 'targeted_regions_method', 'targeted_region_bed_file',
            'date_data_generation', 'target_insert_size', 'sequencing_platform',
        ])
        self.assertIn([
            'Broad_exome_VCGS_FAM203_621_D2', 'Broad_SM-JDBTM', 'VCGS_FAM203_621_D2', 'Kapa HyperPrep', '151', 'exome',
            'Twist', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2022-08-15', '385', 'NovaSeq',
        ], experiment_file)
        self.assertIn([
            'Broad_exome_NA20888', 'Broad_SM-L5QMP', 'NA20888', 'Kapa HyperPrep', '151', 'exome',
            'Twist', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2022-06-05', '380', 'NovaSeq',
        ], experiment_file)
        self.assertEqual([
             'Broad_genome_NA20888_1', 'Broad_SM-L5QMWP', 'NA20888_1', 'Kapa HyperPrep w/o amplification', '200', 'genome',
             '', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2023-03-13', '450', 'NovaSeq2',
        ] in experiment_file, has_second_project)

        self.assertEqual(len(read_file), num_airtable_rows)
        self.assertEqual(read_file[0], [
            'aligned_dna_short_read_id', 'experiment_dna_short_read_id', 'aligned_dna_short_read_file',
            'aligned_dna_short_read_index_file', 'md5sum', 'reference_assembly', 'reference_assembly_uri', 'reference_assembly_details',
            'mean_coverage', 'alignment_software', 'analysis_details',  'quality_issues',
        ])
        self.assertIn([
            'Broad_exome_VCGS_FAM203_621_D2_1', 'Broad_exome_VCGS_FAM203_621_D2',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.crai',
            '129c28163df082', 'GRCh38', '', '', '', 'BWA-MEM-2.3', 'DOI:10.5281/zenodo.4469317', '',
        ], read_file)
        self.assertIn([
            'Broad_exome_NA20888_1', 'Broad_exome_NA20888',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.crai', 'a6f6308866765ce8', 'GRCh38', '', '',
            '42.8', 'BWA-MEM-2.3', '', '',
        ], read_file)
        self.assertEqual([
             'Broad_genome_NA20888_1_1', 'Broad_genome_NA20888_1',
             'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.cram',
             'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.crai', '2aa33e8c32020b1c', 'GRCh38', '', '',
             '36.1', 'BWA-MEM-2.3', '', '',
        ] in read_file, has_second_project)

        self.assertEqual(len(read_set_file), num_airtable_rows)
        self.assertEqual(read_set_file[0], ['aligned_dna_short_read_set_id', 'aligned_dna_short_read_id'])
        self.assertIn(['BCM_H7YG5DSX2', 'Broad_exome_VCGS_FAM203_621_D2_1'], read_set_file)
        self.assertIn(['Broad_NA20888_D1', 'Broad_exome_NA20888_1'], read_set_file)
        self.assertEqual(['Broad_NA20888_D1', 'Broad_genome_NA20888_1_1'] in read_set_file, has_second_project)

        self.assertEqual(len(called_file), 2)
        self.assertEqual(called_file[0], [
            'called_variants_dna_short_read_id', 'aligned_dna_short_read_set_id', 'called_variants_dna_file', 'md5sum',
            'caller_software', 'variant_types', 'analysis_details',
        ])
        self.assertIn([
            'SX2-3', 'BCM_H7YG5DSX2', 'gs://fc-fed09429-e563-44a7-aaeb-776c8336ba02/COL_FAM1_1_D1.SV.vcf',
            '129c28163df082', 'gatk4.1.2', 'SNV', 'DOI:10.5281/zenodo.4469317',
        ], called_file)

        self.assertEqual(len(experiment_rna_file), 2)
        self.assertEqual(experiment_rna_file[0], [
            'experiment_rna_short_read_id', 'analyte_id', 'experiment_sample_id', 'seq_library_prep_kit_method',
            'read_length', 'experiment_type', 'date_data_generation', 'sequencing_platform', 'library_prep_type',
            'single_or_paired_ends', 'within_site_batch_name', 'RIN', 'estimated_library_size', 'total_reads',
            'percent_rRNA', 'percent_mRNA', '5prime3prime_bias', 'percent_mtRNA', 'percent_Globin', 'percent_UMI',
            'percent_GC', 'percent_chrX_Y',
        ])
        self.assertEqual(experiment_rna_file[1], [
            'Broad_paired-end_NA19679', 'Broad_SM-N1P91', 'NA19679', 'Unknown', '151', 'paired-end', '2023-02-11',
            'NovaSeq', 'stranded poly-A pulldown', 'paired-end', 'LCSET-26942', '8.9818', '19480858', '106842386',
            '5.9', '80.2', '1.05', '', '', '', '', '',
        ])

        self.assertEqual(len(aligned_rna_file), 2)
        self.assertEqual(aligned_rna_file[0], [
            'aligned_rna_short_read_id', 'experiment_rna_short_read_id', 'aligned_rna_short_read_file',
            'aligned_rna_short_read_index_file', 'md5sum', 'reference_assembly', 'reference_assembly_uri',
            'reference_assembly_details', 'mean_coverage', 'gene_annotation', 'gene_annotation_details',
            'alignment_software', 'alignment_log_file', 'alignment_postprocessing', 'percent_uniquely_aligned',
            'percent_multimapped', 'percent_unaligned', 'quality_issues'
        ])
        self.assertEqual(aligned_rna_file[1], [
            'Broad_paired-end_NA19679_1', 'Broad_paired-end_NA19679', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.crai', 'f6490b8ebdf2', 'GRCh38',
            'gs://gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta', '', '', 'GENCODEv26', '',
            'STARv2.7.10b', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Log.final.out', '', '80.53', '17.08',
            '1.71', ''
        ])

        self.assertEqual(len(experiment_lookup_file), num_airtable_rows + 1)
        self.assertEqual(experiment_lookup_file[0], ['experiment_id', 'table_name', 'id_in_table', 'participant_id'])
        self.assertIn([
            'experiment_rna_short_read.Broad_paired-end_NA19679', 'experiment_rna_short_read',
            'Broad_paired-end_NA19679', 'Broad_NA19679',
        ], experiment_lookup_file)
        self.assertIn([
            'experiment_dna_short_read.Broad_exome_VCGS_FAM203_621_D2', 'experiment_dna_short_read',
            'Broad_exome_VCGS_FAM203_621_D2', 'Broad_HG00731',
        ], experiment_lookup_file)
        self.assertIn([
            'experiment_dna_short_read.Broad_exome_NA20888', 'experiment_dna_short_read', 'Broad_exome_NA20888',
            'Broad_NA20888',
        ], experiment_lookup_file)
        self.assertEqual([
            'experiment_dna_short_read.Broad_genome_NA20888_1', 'experiment_dna_short_read', 'Broad_genome_NA20888_1',
            'Broad_NA20888',
        ] in experiment_lookup_file, has_second_project)

        self.assertEqual(len(genetic_findings_file), 5 if has_second_project else 3)
        self.assertEqual(genetic_findings_file[0], [
            'genetic_findings_id', 'participant_id', 'experiment_id', 'variant_type', 'variant_reference_assembly',
            'chrom', 'pos', 'ref', 'alt', 'ClinGen_allele_ID', 'gene', 'transcript', 'hgvsc', 'hgvsp', 'zygosity',
            'allele_balance_or_heteroplasmy_percentage', 'variant_inheritance', 'linked_variant', 'linked_variant_phase',
            'gene_known_for_phenotype', 'known_condition_name', 'condition_id', 'condition_inheritance',
            'phenotype_contribution', 'partial_contribution_explained', 'additional_family_members_with_variant',
            'method_of_discovery', 'notes',
        ])
        self.assertIn([
            'Broad_NA19675_1_21_3343353', 'Broad_NA19675_1', '', 'SNV/INDEL', 'GRCh37', '21', '3343353', 'GAGA', 'G', '',
            'RP11', 'ENST00000258436', 'c.375_377delTCT', 'p.Leu126del', 'Heterozygous', '', 'de novo', '', '', 'Known',
            'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects', 'OMIM:615120', 'Autosomal recessive|X-linked',
            'Full', '', '', 'SR-ES', '',
        ], genetic_findings_file)
        self.assertIn([
            'Broad_HG00731_1_248367227', 'Broad_HG00731', 'Broad_exome_VCGS_FAM203_621_D2', 'SNV/INDEL', 'GRCh37', '1',
            '248367227', 'TC', 'T', '', 'RP11', '', '', '', 'Homozygous', '', 'paternal', '', '', 'Known', '',
            'MONDO:0044970', '', 'Full', '', 'Broad_Broad_HG00732', 'SR-ES', '',
        ], genetic_findings_file)
        if has_second_project:
            self.assertIn([
                'Broad_NA20889_1_248367227', 'Broad_NA20889', '', 'SNV/INDEL', 'GRCh37', '1', '248367227', 'TC', 'T',
                '', 'OR4G11P', 'ENST00000505820', 'c.3955G>A', 'c.1586-17C>G', 'Heterozygous', '', 'unknown',
                'Broad_NA20889_1_249045487', '', 'Known', 'IRIDA syndrome', 'MONDO:0008788', 'Autosomal dominant',
                'Full', '', '', 'SR-ES', '',
            ], genetic_findings_file)
            self.assertIn([
                'Broad_NA20889_1_249045487', 'Broad_NA20889', '', 'SNV/INDEL', 'GRCh37', '1', '249045487', 'A', 'G', '',
                'OR4G11P', '', '', '', 'Heterozygous', '', 'unknown', 'Broad_NA20889_1_248367227', '', 'Known',
                'IRIDA syndrome', 'MONDO:0008788', 'Autosomal dominant', 'Full', '', '', 'SR-ES', '',
            ], genetic_findings_file)

    def _test_expected_gregor_airtable_calls(self, additional_samples=None, additional_mondo_ids=None):
        mondo_ids = ['0044970'] + (additional_mondo_ids or [])
        self.assertEqual(len(responses.calls), len(mondo_ids) + 4)
        self.assertSetEqual(
            {call.request.url for call in responses.calls[:len(mondo_ids)]},
            {f'https://monarchinitiative.org/v3/api/entity/MONDO:{mondo_id}' for mondo_id in mondo_ids}
        )

        sample_ids = {
             'HG00731', 'HG00732', 'HG00733', 'NA19675_1', 'NA19678', 'NA19679', 'NA20870', 'NA20872', 'NA20874',
             'NA20875', 'NA20876', 'NA20881', 'NA20888',
        }
        sample_ids.update(additional_samples or [])
        sample_filter = ','.join([f"{{CollaboratorSampleID}}='{sample_id}'" for sample_id in sorted(sample_ids)])
        sample_fields = ['CollaboratorSampleID', 'SMID', 'CollaboratorParticipantID', 'Recontactable']
        self.assert_expected_airtable_call(len(mondo_ids), f"OR({sample_filter})", sample_fields)
        sample_ids -= {'NA19675_1', 'NA19679', 'NA20888'}
        secondary_sample_filter = ','.join([f"{{SeqrCollaboratorSampleID}}='{sample_id}'" for sample_id in sorted(sample_ids)])
        sample_fields[0] = 'SeqrCollaboratorSampleID'
        self.assert_expected_airtable_call(len(mondo_ids) + 1, f"OR({secondary_sample_filter})", sample_fields)
        metadata_fields = [
            'CollaboratorParticipantID', '5prime3prime_bias_rna', 'CollaboratorSampleID_rna', 'CollaboratorSampleID_wes',
            'CollaboratorSampleID_wgs', 'RIN_rna', 'SMID_rna', 'SMID_wes', 'SMID_wgs', 'aligned_dna_short_read_file_wes',
            'aligned_dna_short_read_file_wgs', 'aligned_dna_short_read_index_file_wes',
            'aligned_dna_short_read_index_file_wgs', 'aligned_dna_short_read_set_id',
            'aligned_rna_short_read_file', 'aligned_rna_short_read_index_file', 'alignment_log_file_rna',
            'alignment_software_dna', 'alignment_software_rna', 'analysis_details', 'called_variants_dna_file',
            'called_variants_dna_short_read_id', 'caller_software', 'date_data_generation_rna', 'date_data_generation_wes',
            'date_data_generation_wgs', 'estimated_library_size_rna', 'experiment_type_rna', 'experiment_type_wes',
            'experiment_type_wgs', 'gene_annotation_rna', 'library_prep_type_rna', 'md5sum_rna', 'md5sum_wes',
            'md5sum_wgs', 'mean_coverage_wes', 'mean_coverage_wgs', 'percent_mRNA', 'percent_multimapped_rna',
            'percent_rRNA', 'percent_unaligned_rna', 'percent_uniquely_aligned_rna', 'read_length_rna', 'read_length_wes',
            'read_length_wgs', 'reference_assembly', 'reference_assembly_uri_rna', 'seq_library_prep_kit_method_rna',
            'seq_library_prep_kit_method_wes', 'seq_library_prep_kit_method_wgs', 'sequencing_platform_rna',
            'sequencing_platform_wes', 'sequencing_platform_wgs', 'single_or_paired_ends_rna', 'target_insert_size_wes',
            'target_insert_size_wgs', 'targeted_region_bed_file', 'targeted_regions_method_wes', 'total_reads_rna',
            'variant_types', 'within_site_batch_name_rna',
        ]
        self.assert_expected_airtable_call(
            len(mondo_ids) + 2, "OR(CollaboratorParticipantID='NA19675',CollaboratorParticipantID='NA19679',CollaboratorParticipantID='NA20888',CollaboratorParticipantID='VCGS_FAM203_621')",
            metadata_fields,
        )

        self.assertEqual(responses.calls[len(mondo_ids) + 3].request.url, MOCK_DATA_MODEL_URL)


class LocalReportAPITest(AuthenticationTestCase, ReportAPITest):
    fixtures = ['users', '1kg_project', 'reference_data', 'report_variants']
    STATS_DATA = {
        'projectsCount': {'non_demo': 3, 'demo': 1},
        'familiesCount': {'non_demo': 12, 'demo': 2},
        'individualsCount': {'non_demo': 16, 'demo': 4},
        'sampleCountsByType': {
            'WES__SNV_INDEL': {'demo': 1, 'non_demo': 7},
            'WGS__MITO': {'non_demo': 1},
            'WES__SV': {'non_demo': 3},
            'WGS__SV': {'non_demo': 1},
            'RNA__SNV_INDEL': {'non_demo': 3},
        },
    }


class AnvilReportAPITest(AnvilAuthenticationTestCase, ReportAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'report_variants']
    STATS_DATA = {
        'projectsCount': {'internal': 1, 'external': 1, 'no_anvil': 1, 'demo': 1},
        'familiesCount': {'internal': 11, 'external': 1, 'no_anvil': 0, 'demo': 2},
        'individualsCount': {'internal': 14, 'external': 2, 'no_anvil': 0, 'demo': 4},
        'sampleCountsByType': {
            'WES__SNV_INDEL': {'internal': 7, 'demo': 1},
            'WGS__MITO': {'internal': 1},
            'WES__SV': {'internal': 3},
            'WGS__SV': {'external': 1},
            'RNA__SNV_INDEL': {'internal': 3},
        },
    }
