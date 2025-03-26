from django.urls.base import reverse
import json
import mock
import responses
from settings import AIRTABLE_URL

from seqr.models import Project, SavedVariant
from seqr.views.apis.report_api import seqr_stats, anvil_export, gregor_export, family_metadata, variant_metadata
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, AirtableTest


PROJECT_GUID = 'R0001_1kg'
NO_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'

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
      "id": "rec2Nkg10N1KssX1c",
      "fields": {
        'SeqrCollaboratorSampleID': 'NA19679',
        'CollaboratorSampleID': 'NA19679',
        'CollaboratorParticipantID': 'NA19679',
        'SMID': 'SM-X1P92',
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

AIRTABLE_RNA_ONLY_GREGOR_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B67GmXpAkQW8z",
      "fields": {
        'SMID': 'SM-N1P91',
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
        'SMID_rna': ['rec2B67GmXpAkQW8z'],
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
        'Primary_Biosample_rna': ['Liver', 'Fibroblast'],
        'RIN_rna': '8.9818',
        'tissue_affected_status_rna': 'Yes',
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
                {'column': 'solve_status', 'required': True, 'data_type': 'enumeration', 'enumerations': ['Solved', 'Partially solved', 'Probably solved', 'Unsolved', 'Unaffected']},
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
                {'column': 'sequencing_event_details'},
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
                {'column': 'aligned_dna_short_read_set_id', 'primary_key': True},
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
                {'column': 'variant_type', 'required': True, 'data_type': 'enumeration', 'enumerations': ['SNV', 'INDEL', 'SV', 'CNV', 'RE', 'MEI']},
                {'column': 'variant_reference_assembly', 'required': True, 'data_type': 'enumeration', 'enumerations': ['GRCh37', 'GRCh38']},
                {'column': 'chrom', 'required': True},
                {'column': 'pos', 'required': True, 'data_type': 'integer'},
                {'column': 'ref','required': 'CONDITIONAL (variant_type = SNV, variant_type = INDEL, variant_type = RE)'},
                {'column': 'alt', 'required': 'CONDITIONAL (variant_type = SNV, variant_type = INDEL, variant_type = RE)'},
                {'column': 'ClinGen_allele_ID'},
                {'column': 'gene_of_interest', 'required': True},
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
                {'column': 'notes'},
                {'column': 'sv_type'},
                {'column': 'chrom_end'},
                {'column': 'pos_end', 'data_type': 'integer'},
                {'column': 'copy_number', 'data_type': 'integer'},
                {'column': 'hgvs'},
                {'column': 'gene_disease_validity'},
            ]
        },
    ]
}
MOCK_DATA_MODEL_RESPONSE = json.dumps(MOCK_DATA_MODEL, indent=2).replace('"references"', '//"references"')

INVALID_MODEL_TABLES = {
    'participant': {
        'internal_project_id': {'data_type': 'reference'},
        'prior_testing': {'data_type': 'enumeration', 'required': 'CONDITIONAL (proband_relationship = Self, proband_relationship = Father)'},
        'proband_relationship': {'required': 'CONDITIONAL (sex = Male)'},
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
    'genetic_findings': {'experiment_id': {'required': True, 'primary_key': True}},
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

BASE_VARIANT_METADATA_ROW = {
    'internal_project_id': '1kg project nåme with uniçøde',
    'ClinGen_allele_ID': None,
    'MME': False,
    'additional_family_members_with_variant': '',
    'allele_balance_or_heteroplasmy_percentage': None,
    'analysisStatus': 'Q',
    'chrom_end': None,
    'clinvar': None,
    'condition_id': None,
    'copy_number': None,
    'pos_end': None,
    'hgvsc': '',
    'hgvsp': '',
    'method_of_discovery': 'SR-ES',
    'notes': '',
    'phenotype_contribution': 'Full',
    'partial_contribution_explained': '',
    'seqr_chosen_consequence': None,
    'sv_type': None,
    'sv_name': None,
    'transcript': None,
    'validated_name': None,
    'variant_type': 'INDEL',
}

PARTICIPANT_TABLE = [
    [
        'participant_id', 'internal_project_id', 'gregor_center', 'consent_code', 'recontactable', 'prior_testing',
        'pmid_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id', 'proband_relationship',
        'proband_relationship_detail', 'sex', 'sex_detail', 'reported_race', 'reported_ethnicity', 'ancestry_detail',
        'age_at_last_observation', 'affected_status', 'phenotype_description', 'age_at_enrollment', 'solve_status',
        'missing_variant_case',
    ], [
        'Broad_NA19675_1', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', 'Yes', 'IKBKAP|CCDC102B|CMA - normal',
        '34415322', 'Broad_1', 'Broad_NA19678', 'Broad_NA19679', '', 'Self', '', 'Male', 'XXY',
        'Middle Eastern or North African', '', '', '21', 'Affected', 'myopathy', '18', 'Unsolved', 'No',
    ], [
        'Broad_HG00731', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_2', 'Broad_HG00732',
        'Broad_HG00733', '', 'Self', '', 'Female', 'X0', '', 'Hispanic or Latino', 'Other', '', 'Affected',
        'microcephaly; seizures', '', 'Unsolved', 'No',
    ], [
        'Broad_HG00732', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_2', '0', '0', '',
        'Father', '', 'Male', '', 'White', '', '', '', 'Unaffected', 'microcephaly; seizures', '', 'Unaffected', 'No',
    ], [
        'Broad_NA20876', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_7', '0',
        '0', '', '', '', 'Male', '', '', '', '', '', 'Affected', '', '', 'Solved', 'No',
    ], [
        'Broad_NA20888', 'Broad_Test Reprocessed Project', 'BROAD', 'HMB', 'No', '', '', 'Broad_12', '0', '0', '', '',
        '', 'Male', '', 'Asian', '', 'South Asian', '', 'Affected', '', '', 'Unsolved', 'No',
    ], [
        'Broad_NA20889', 'Broad_Test Reprocessed Project', 'BROAD', 'HMB', '', '', '', 'Broad_12', '0', '0', '', 'Self',
        '', 'Female', '', 'White', '', 'Ashkenazi Jewish', '', 'Affected', '', '', 'Partially solved', 'No',
    ],
]

PHENOTYPE_TABLE = [
    [
        'phenotype_id', 'participant_id', 'term_id', 'presence', 'ontology', 'additional_details',
        'onset_age_range', 'additional_modifiers',
    ],
    ['', 'Broad_NA19675_1', 'HP:0002011', 'Present', 'HPO', '', 'HP:0003593', 'HP:0012825|HP:0003680'],
    ['', 'Broad_NA19675_1', 'HP:0001674', 'Absent', 'HPO', 'originally indicated', '', ''],
    ['', 'Broad_HG00731', 'HP:0011675', 'Present', 'HPO', '', '', ''],
    ['', 'Broad_HG00731', 'HP:0002017', 'Absent', 'HPO', '', '', ''],
    ['', 'Broad_NA20889', 'HP:0011675', 'Present', 'HPO', '', '', ''],
    ['', 'Broad_NA20889', 'HP:0001509', 'Present', 'HPO', '', '', ''],
]

EXPERIMENT_TABLE = [
    [
        'experiment_dna_short_read_id', 'analyte_id', 'experiment_sample_id', 'seq_library_prep_kit_method',
        'read_length', 'experiment_type', 'targeted_regions_method', 'targeted_region_bed_file',
        'date_data_generation', 'target_insert_size', 'sequencing_platform', 'sequencing_event_details',
    ], [
        'Broad_exome_VCGS_FAM203_621_D2', 'Broad_SM-JDBTM', 'VCGS_FAM203_621_D2', 'Kapa HyperPrep', '151', 'exome',
        'Twist', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2022-08-15', '385', 'NovaSeq', '',
    ], [
        'Broad_exome_NA20888', 'Broad_SM-L5QMP', 'NA20888', 'Kapa HyperPrep', '151', 'exome',
        'Twist', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2022-06-05', '380', 'NovaSeq', '',
    ], [
         'Broad_genome_NA20888_1', 'Broad_SM-L5QMWP', 'NA20888_1', 'Kapa HyperPrep w/o amplification', '200', 'genome',
         '', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2023-03-13', '450', 'NovaSeq2', '',
    ],
]

EXPERIMENT_LOOKUP_TABLE = [
    [
        'experiment_id', 'table_name', 'id_in_table', 'participant_id',
    ], [
        'experiment_rna_short_read.Broad_paired-end_NA19679', 'experiment_rna_short_read',
        'Broad_paired-end_NA19679', 'Broad_NA19679',
    ], [
        'experiment_dna_short_read.Broad_exome_VCGS_FAM203_621_D2', 'experiment_dna_short_read',
        'Broad_exome_VCGS_FAM203_621_D2', 'Broad_HG00731',
    ], [
        'experiment_dna_short_read.Broad_exome_NA20888', 'experiment_dna_short_read', 'Broad_exome_NA20888',
        'Broad_NA20888',
    ], [
        'experiment_dna_short_read.Broad_genome_NA20888_1', 'experiment_dna_short_read', 'Broad_genome_NA20888_1',
        'Broad_NA20888',
    ]
]

GENETIC_FINDINGS_TABLE = [
    [
        'genetic_findings_id', 'participant_id', 'experiment_id', 'variant_type', 'variant_reference_assembly',
        'chrom', 'pos', 'ref', 'alt', 'ClinGen_allele_ID', 'gene_of_interest', 'transcript', 'hgvsc', 'hgvsp', 'zygosity',
        'allele_balance_or_heteroplasmy_percentage', 'variant_inheritance', 'linked_variant', 'linked_variant_phase',
        'gene_known_for_phenotype', 'known_condition_name', 'condition_id', 'condition_inheritance',
        'phenotype_contribution', 'partial_contribution_explained', 'additional_family_members_with_variant',
        'method_of_discovery', 'notes', 'sv_type', 'chrom_end', 'pos_end', 'copy_number', 'hgvs', 'gene_disease_validity',
    ], [
        'Broad_NA19675_1_21_3343353', 'Broad_NA19675_1', '', 'INDEL', 'GRCh37', '21', '3343353', 'GAGA', 'G', '',
        'RP11', 'ENST00000258436.5', 'c.375_377delTCT', 'p.Leu126del', 'Heterozygous', '', 'de novo', '', '', 'Candidate',
        'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects', 'OMIM:615120', 'Autosomal recessive|X-linked',
        'Full', '', '', 'SR-ES', 'This individual is published in PMID34415322', '', '', '', '', '', '',
    ], [
        'Broad_HG00731_1_248367227', 'Broad_HG00731', 'Broad_exome_VCGS_FAM203_621_D2', 'INDEL', 'GRCh37', '1',
        '248367227', 'TC', 'T', 'CA1501729', 'RP11', '', '', '', 'Homozygous', '', 'paternal', '', '', 'Known', '',
        'MONDO:0044970', '', 'Uncertain', '', 'Broad_HG00732', 'SR-ES', '', '', '', '', '', '', '',
    ], [
        'Broad_HG00731_19_1912632', 'Broad_HG00731', 'Broad_exome_VCGS_FAM203_621_D2', 'SNV', 'GRCh38', '19',
        '1912632', 'G', 'C', '', 'OR4G11P', 'ENST00000371839', 'c.586_587delinsTT', 'p.Ala196Leu', 'Heterozygous', '', 'unknown',
        'Broad_HG00731_19_1912634', '', 'Known', '', 'MONDO:0044970', '', 'Full', '', '', 'SR-ES',
        'The following variants are part of the multinucleotide variant 19-1912632-G-C (c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T',
        '', '', '', '', '', '',
    ], [
        'Broad_NA20889_1_248367227', 'Broad_NA20889', '', 'INDEL', 'GRCh37', '1', '248367227', 'TC', 'T',
        'CA1501729', 'OR4G11P', 'ENST00000505820', 'c.3955G>A', 'c.1586-17C>G', 'Heterozygous', '', 'unknown',
        'Broad_NA20889_1_249045487_DEL', '', 'Candidate', 'Immunodeficiency 38', 'OMIM:616126', 'Autosomal recessive',
        'Partial', 'HP:0000501|HP:0000365', '', 'SR-ES', '', '', '', '', '', '', '',
    ], [
        'Broad_NA20889_1_249045487_DEL', 'Broad_NA20889', '', 'SV', 'GRCh37', '1', '249045487', '', '', '',
        'OR4G11P', '', '', '', 'Heterozygous', '', 'unknown', 'Broad_NA20889_1_248367227', '', 'Candidate',
        'Immunodeficiency 38', 'OMIM:616126', 'Autosomal recessive', 'Full', '', '', 'SR-ES',
        'Phasing incorrect in input VCF', 'DEL', '', '249045898', '1', 'DEL:chr1:249045123-249045456', '',
    ],
]

READ_TABLE_HEADER = [
    'aligned_dna_short_read_id', 'experiment_dna_short_read_id', 'aligned_dna_short_read_file',
    'aligned_dna_short_read_index_file', 'md5sum', 'reference_assembly', 'reference_assembly_uri',
    'reference_assembly_details', 'mean_coverage', 'alignment_software', 'analysis_details', 'quality_issues',
]
READ_SET_TABLE_HEADER = ['aligned_dna_short_read_set_id', 'aligned_dna_short_read_id']
RNA_TABLE_HEADER = [
    'experiment_rna_short_read_id', 'analyte_id', 'experiment_sample_id', 'seq_library_prep_kit_method',
    'read_length', 'experiment_type', 'date_data_generation', 'sequencing_platform', 'library_prep_type',
    'single_or_paired_ends', 'within_site_batch_name', 'RIN', 'estimated_library_size', 'total_reads',
    'percent_rRNA', 'percent_mRNA', '5prime3prime_bias', 'percent_mtRNA', 'percent_Globin', 'percent_UMI',
    'percent_GC', 'percent_chrX_Y',
]


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

        self.check_no_analyst_no_access(url, has_override=self.HAS_PM_OVERRIDE)

    @mock.patch('seqr.views.utils.export_utils.zipfile.ZipFile')
    @responses.activate
    def test_anvil_export(self, mock_zip):
        url = reverse(anvil_export, args=[PROJECT_GUID])
        self.check_analyst_login(url)

        no_analyst_project_url = reverse(anvil_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(no_analyst_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), json=AIRTABLE_SAMPLE_RECORDS, status=200)
        response = self.client.get(url)
        self._check_anvil_export_response(response, mock_zip, no_analyst_project_url)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        self.check_no_analyst_no_access(url)

    def _check_anvil_export_response(self, response, mock_zip, no_analyst_project_url):
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
            'dbgap_subject_id_1', 'No', '1', 'NA19678', 'NA19679', '-', 'Self', 'Male', 'Middle Eastern or North African', '-', '-',
            '-', 'OMIM:615120', 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
            'Affected', 'Adult onset', '-', 'HP:0001631|HP:0002011|HP:0001636', 'HP:0011675|HP:0001674|HP:0001508',
            'myopathy', 'Unsolved'], subject_file)

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
            '1_248367227_HG00731', 'HG00731', 'HG00731', 'RP11', 'Known', 'paternal',
            'Homozygous', 'GRCh37', '1', '248367227', 'TC', 'T', '-', '-', '-', '-', '-', '-', '-'], discovery_file)
        self.assertIn([
            '21_3343353_NA19675_1', 'NA19675_1', 'NA19675', 'RP11', 'Candidate', 'de novo',
            'Heterozygous', 'GRCh37', '21', '3343353', 'GAGA', 'G', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436.5',
            '-', '-', '-', 'This individual is published in PMID34415322'], discovery_file)
        self.assertIn([
            '19_1912633_HG00731', 'HG00731', 'HG00731', 'OR4G11P', 'Known', 'unknown', 'Heterozygous', 'GRCh38', '19',
            '1912633', 'G', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-G-C '
            '(c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)
        self.assertIn([
            '19_1912634_HG00731', 'HG00731', 'HG00731', 'OR4G11P', 'Known', 'unknown', 'Heterozygous', 'GRCh38', '19',
            '1912634', 'C', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-G-C (c.586_587delinsTT, '
            'p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)

        self.login_data_manager_user()
        self.mock_get_groups.side_effect = lambda user: ['Analysts']
        response = self.client.get(no_analyst_project_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors'],
                         ['Discovery variant(s) 1-248367227-TC-T in family 14 have no associated gene'])

    @mock.patch('seqr.views.apis.report_api.GREGOR_DATA_MODEL_URL', MOCK_DATA_MODEL_URL)
    @mock.patch('seqr.views.apis.report_api.datetime')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @responses.activate
    def test_gregor_export(self, *args):
        url = reverse(gregor_export)
        self.check_analyst_login(url)

        self._test_gregor_export(url, *args)

    def _test_gregor_export(self, url, mock_subprocess, mock_temp_dir, mock_open, mock_datetime):
        mock_datetime.now.return_value.year = 2020
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        mock_subprocess.return_value.wait.return_value = 1

        airtable_sample_url = f'{AIRTABLE_URL}/app3Y97xtbbaOopVR/Samples'
        responses.add(
            responses.GET, airtable_sample_url, json=AIRTABLE_GREGOR_SAMPLE_RECORDS, status=200, match=[
                responses.matchers.query_param_matcher({'fields[]': ['CollaboratorSampleID', 'CollaboratorParticipantID', 'Recontactable', 'SMID']}, strict_match=False),
            ]
        )
        responses.add(
            responses.GET, airtable_sample_url, json=AIRTABLE_GREGOR_SAMPLE_RECORDS, status=200, match=[
                responses.matchers.query_param_matcher({'fields[]': ['SeqrCollaboratorSampleID', 'CollaboratorParticipantID', 'Recontactable', 'SMID']}, strict_match=False),
            ]
        )
        responses.add(
            responses.GET, airtable_sample_url, json=AIRTABLE_RNA_ONLY_GREGOR_SAMPLE_RECORDS, status=200,
            match=[responses.matchers.query_param_matcher({'fields[]': 'SMID'}, strict_match=False)]
        )
        responses.add(
            responses.GET, '{}/app3Y97xtbbaOopVR/GREGoR Data Model'.format(AIRTABLE_URL), json=AIRTABLE_GREGOR_RECORDS,
            status=200)

        responses.add(responses.GET, MOCK_DATA_MODEL_URL, status=404)

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
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Unable to load data model: 404 Client Error: Not Found for url: http://raw.githubusercontent.com/gregor_data_model.json',
        ])

        responses.add(responses.GET, MOCK_DATA_MODEL_URL, json=MOCK_INVALID_DATA_MODEL, status=200)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)

        recommended_warnings = [
            'The following entries are missing RNA airtable data: NA19675',
            'The following entries are missing WES airtable data: NA19675, NA19679',
            'The following entries have WGS airtable data but do not have equivalent loaded data in seqr, so airtable data is omitted: NA19675, NA20888, VCGS_FAM203_621',
            'The following entries are missing recommended "recontactable" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881',
            'The following entries are missing recommended "reported_race" in the "participant" table: Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "phenotype_description" in the "participant" table: Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "age_at_enrollment" in the "participant" table: Broad_HG00731, Broad_NA20870, Broad_NA20872, Broad_NA20875, Broad_NA20876, Broad_NA20881, Broad_NA20888',
            'The following entries are missing recommended "known_condition_name" in the "genetic_findings" table: Broad_HG00731_19_1912632, Broad_HG00731_1_248367227',
        ]
        validation_warnings = [
            'The following columns are specified as "enumeration" in the "participant" data model but are missing the allowed values definition: prior_testing',
            'The following columns are included in the "participant" data model but have an unsupported data type: internal_project_id (reference)',
            'The following columns are computed for the "participant" table but are missing from the data model: age_at_last_observation, ancestry_detail, missing_variant_case, pmid_id',
        ] + recommended_warnings
        self.assertListEqual(response.json()['warnings'], validation_warnings)
        missing_participant_error = 'The following participants are missing CollaboratorParticipantID for the airtable Sample: Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881'
        validation_errors = [
            f'No data model found for "{file}" table' for file in reversed(EXPECTED_GREGOR_FILES) if file not in INVALID_MODEL_TABLES
        ] + [
            missing_participant_error,
            'The following tables are required in the data model but absent from the reports: subject, dna_read_data_set',
        ] + [
            'The following entries are missing required "prior_testing" in the "participant" table: Broad_HG00731, Broad_HG00732',
            'The following entries are missing required "proband_relationship" in the "participant" table: Broad_NA19678, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20881',
            'The following entries have invalid values for "reported_race" in the "participant" table. Allowed values: Asian, White, Black. Invalid values: Broad_NA19675_1 (Middle Eastern or North African)',
            'The following entries have invalid values for "age_at_enrollment" in the "participant" table. Allowed values have data type date. Invalid values: Broad_NA19675_1 (18)',
            'The following entries have invalid values for "reference_assembly" (from Airtable) in the "aligned_dna_short_read" table. Allowed values have data type integer. Invalid values: Broad_exome_NA20888_1 (GRCh38), Broad_exome_VCGS_FAM203_621_D2_1 (GRCh38)',
            'The following entries are missing required "mean_coverage" (from Airtable) in the "aligned_dna_short_read" table: Broad_exome_VCGS_FAM203_621_D2_1',
            'The following entries have non-unique values for "alignment_software" (from Airtable) in the "aligned_dna_short_read" table: BWA-MEM-2.3 (Broad_exome_NA20888_1, Broad_exome_VCGS_FAM203_621_D2_1)',
            'The following entries have invalid values for "analysis_details" (from Airtable) in the "aligned_dna_short_read" table. Allowed values are a google bucket path starting with gs://. Invalid values: Broad_exome_VCGS_FAM203_621_D2_1 (DOI:10.5281/zenodo.4469317)',
            'The following entries have invalid values for "date_data_generation" (from Airtable) in the "experiment_rna_short_read" table. Allowed values have data type float. Invalid values: NA19679 (2023-02-11)',
            'The following entries are missing required "experiment_id" (from Airtable) in the "genetic_findings" table: Broad_NA19675_1_21_3343353',
            'The following entries have non-unique values for "experiment_id" (from Airtable) in the "genetic_findings" table: Broad_exome_VCGS_FAM203_621_D2 (Broad_HG00731_19_1912632, Broad_HG00731_1_248367227)',
        ]
        self.assertListEqual(response.json()['errors'], validation_errors)

        mock_open.reset_mock()
        response = self.client.post(
            url, content_type='application/json', data=json.dumps({**body, 'overrideValidation': True})
        )
        self.assertEqual(response.status_code, 200)
        expected_response = {
            'info': ['Successfully validated and uploaded Gregor Report for 9 families'],
            'warnings': validation_errors + validation_warnings,
        }
        self.assertDictEqual(response.json(), expected_response)
        participant_file, read_file, read_set_file, rna_file, genetic_findings_file = self._get_expected_gregor_files(
            mock_open, mock_subprocess, INVALID_MODEL_TABLES.keys()
        )
        self._assert_expected_file(participant_file, [
            [c for c in PARTICIPANT_TABLE[0] if c not in {'pmid_id', 'ancestry_detail', 'age_at_last_observation', 'missing_variant_case'}],
            [
            'Broad_NA19675_1', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', 'Yes', 'IKBKAP|CCDC102B|CMA - normal',
            'Broad_1', 'Broad_NA19678', 'Broad_NA19679', '', 'Self', '', 'Male', 'XXY', 'Middle Eastern or North African',
            '', 'Affected', 'myopathy', '18', 'Unsolved',
        ], [
            'Broad_NA19678', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', 'Broad_1', '0', '0', '', '',
            '', 'Male', '', '', '', 'Unaffected', 'myopathy', '', 'Unaffected',
        ], [
            'Broad_HG00731', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', 'Broad_2', 'Broad_HG00732',
            'Broad_HG00733', '', 'Self', '', 'Female', 'X0', '', 'Hispanic or Latino', 'Affected',
            'microcephaly; seizures', '', 'Unsolved',
        ]], additional_calls=10)
        self._assert_expected_file(read_file, [READ_TABLE_HEADER, [
            'Broad_exome_VCGS_FAM203_621_D2_1', 'Broad_exome_VCGS_FAM203_621_D2',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.crai', '129c28163df082', 'GRCh38', '', '',
            '', 'BWA-MEM-2.3', 'DOI:10.5281/zenodo.4469317', '',
        ]], additional_calls=1)
        self._assert_expected_file(read_set_file, [
            READ_SET_TABLE_HEADER,
            ['Broad_exome_VCGS_FAM203_621_D2', 'Broad_exome_VCGS_FAM203_621_D2_1'],
        ], additional_calls=1)
        self._assert_expected_file(rna_file, [RNA_TABLE_HEADER, [
            'Broad_paired-end_NA19679', 'Broad_SM-N1P91', 'NA19679', 'Unknown', '151', 'paired-end', '2023-02-11',
            'NovaSeq', 'stranded poly-A pulldown', 'paired-end', 'LCSET-26942', '8.9818', '19480858', '106842386', '5.9',
            '80.2', '1.05', '', '', '', '', '',
        ]])
        self._assert_expected_file(genetic_findings_file, [GENETIC_FINDINGS_TABLE[0], [
            'Broad_NA19675_1_21_3343353', 'Broad_NA19675_1', '', 'INDEL', 'GRCh37', '21', '3343353', 'GAGA', 'G', '',
            'RP11', 'ENST00000258436.5', 'c.375_377delTCT', 'p.Leu126del', 'Heterozygous', '', 'de novo', '', '',
            'Candidate', 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects', 'OMIM:615120',
            'Autosomal recessive|X-linked', 'Full', '', '', 'SR-ES', 'This individual is published in PMID34415322',
            '', '', '', '', '', '',
        ], [
            'Broad_HG00731_1_248367227', 'Broad_HG00731', 'Broad_exome_VCGS_FAM203_621_D2', 'INDEL', 'GRCh37', '1',
            '248367227', 'TC', 'T', 'CA1501729', 'RP11', '', '', '', 'Homozygous', '', 'paternal', '', '', 'Known', '',
            'MONDO:0044970', '', 'Uncertain', '', 'Broad_HG00732', 'SR-ES', '', '', '', '', '', '', '',
        ]], additional_calls=1)

        responses.calls.reset()
        mock_subprocess.reset_mock()
        mock_open.reset_mock()
        responses.add(responses.GET, MOCK_DATA_MODEL_URL, body=MOCK_DATA_MODEL_RESPONSE, status=200)
        body['overrideValidation'] = True
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        expected_response['warnings'] = [missing_participant_error] + recommended_warnings
        self.assertDictEqual(response.json(), expected_response)
        self._assert_expected_gregor_files(mock_open, mock_subprocess)
        self._test_expected_gregor_airtable_calls()

        # Test multiple project with shared sample IDs
        project = Project.objects.get(id=3)
        project.consent_code = 'H'
        project.save()

        # For SV variant, test reports in gene associated with OMIM condition even if not annotated
        variant = SavedVariant.objects.get(id=7)
        variant.saved_variant_json['transcripts'] = {'ENSG00000135953': []}
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
        mock_subprocess.reset_mock()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        expected_response['info'][0] = expected_response['info'][0].replace('9', '10')
        expected_response['warnings'][0] = expected_response['warnings'][0].replace('Broad_NA20881', 'Broad_NA20881, Broad_NA20885, Broad_NA20889')
        expected_response['warnings'][3] = expected_response['warnings'][3].replace(', NA20888', '')
        expected_response['warnings'][4] = expected_response['warnings'][4] + ', Broad_NA20885, Broad_NA20889'
        expected_response['warnings'][5] = expected_response['warnings'][5].replace(', Broad_NA20888', '')
        expected_response['warnings'][6] = expected_response['warnings'][6].replace('Broad_NA20888', 'Broad_NA20885, Broad_NA20888, Broad_NA20889')
        expected_response['warnings'][7] = expected_response['warnings'][7].replace('Broad_NA20888', 'Broad_NA20885, Broad_NA20888, Broad_NA20889')
        self.assertDictEqual(response.json(), expected_response)
        self._assert_expected_gregor_files(mock_open, mock_subprocess, has_second_project=True)
        self._test_expected_gregor_airtable_calls(additional_samples=['NA20885', 'NA20889'], additional_mondo_ids=['0008788'])

        self.check_no_analyst_no_access(url)

    def _get_expected_gregor_files(self, mock_open, mock_subprocess, expected_files):
        # test gsutil commands
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://anvil-upload', stdout=-1, stderr=-2, shell=True),  # nosec
            mock.call().wait(),
            mock.call('gsutil mv /mock/tmp/* gs://anvil-upload/', stdout=-1, stderr=-2, shell=True),  # nosec
            mock.call().wait(),
        ])

        self.assertListEqual(
            mock_open.call_args_list, [mock.call(f'/mock/tmp/{file}.tsv', 'w') for file in expected_files])
        return [
            [row.split('\t') for row in write_call.args[0].split('\n')]
            for write_call in mock_open.return_value.__enter__.return_value.write.call_args_list
        ]

    def _assert_expected_gregor_files(self, mock_open, mock_subprocess, has_second_project=False):
        files = self._get_expected_gregor_files(mock_open, mock_subprocess, EXPECTED_GREGOR_FILES)
        participant_file, family_file, phenotype_file, analyte_file, experiment_file, read_file, read_set_file, \
        called_file, experiment_rna_file, aligned_rna_file, experiment_lookup_file, genetic_findings_file = files

        single_project_row = PARTICIPANT_TABLE[5][:1] + ['Broad_1kg project nme with unide'] + PARTICIPANT_TABLE[5][2:7] + [
                'Broad_8'] + PARTICIPANT_TABLE[5][8:13] + ['Female', '', '', '', ''] + PARTICIPANT_TABLE[5][18:]
        self._assert_expected_file(
            participant_file,
            expected_rows=PARTICIPANT_TABLE if has_second_project else PARTICIPANT_TABLE[:5] + [single_project_row],
            absent_rows=[single_project_row] if has_second_project else PARTICIPANT_TABLE[5:],
            additional_calls=9 if has_second_project else 8,
        )

        expected_rows = [
            ['family_id', 'consanguinity', 'consanguinity_detail'],
            ['Broad_1', 'Present', ''],
        ]
        absent_rows = []
        fam_8_row = ['Broad_8', 'Unknown', '']
        fam_11_row = ['Broad_11', 'None suspected', '']
        if has_second_project:
            expected_rows.append(fam_11_row)
            absent_rows.append(fam_8_row)
        else:
            expected_rows.append(fam_8_row)
            absent_rows.append(fam_11_row)
        self._assert_expected_file(
            family_file, expected_rows, absent_rows=absent_rows, additional_calls=8 if has_second_project else 7,
        )

        self._assert_expected_file(
            phenotype_file,
            expected_rows=PHENOTYPE_TABLE if has_second_project else PHENOTYPE_TABLE[:5],
            absent_rows=None if has_second_project else PHENOTYPE_TABLE[5:],
            additional_calls=7 if has_second_project else 5,
        )

        expected_rows = [
            [
                'analyte_id', 'participant_id', 'analyte_type', 'analyte_processing_details', 'primary_biosample',
                'primary_biosample_id', 'primary_biosample_details', 'tissue_affected_status',
            ],
            ['Broad_SM-AGHT', 'Broad_NA19675_1', 'DNA', '', 'UBERON:0003714', '', '', 'No'],
            ['Broad_SM-N1P91', 'Broad_NA19679', 'RNA', '', 'CL: 0000057', '', '', 'Yes'],
            ['Broad_SM-L5QMP', 'Broad_NA20888', '', '', '', '', '', 'No'],
        ]
        absent_rows = []
        (expected_rows if has_second_project else absent_rows).append(
            ['Broad_SM-L5QMWP', 'Broad_NA20888', '', '', '', '', '', 'No']
        )
        self._assert_expected_file(analyte_file, expected_rows, absent_rows=absent_rows, additional_calls=1)

        self._assert_expected_file(
            experiment_file,
            expected_rows=EXPERIMENT_TABLE if has_second_project else EXPERIMENT_TABLE[:3],
            absent_rows=None if has_second_project else EXPERIMENT_TABLE[3:],
        )

        expected_rows = [READ_TABLE_HEADER, [
            'Broad_exome_NA20888_1', 'Broad_exome_NA20888',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888.crai', 'a6f6308866765ce8', 'GRCh38', '', '',
            '42.8', 'BWA-MEM-2.3', '', '',
        ]]
        absent_rows = []
        (expected_rows if has_second_project else absent_rows).append([
             'Broad_genome_NA20888_1_1', 'Broad_genome_NA20888_1',
             'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.cram',
             'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_NA20888_1.crai', '2aa33e8c32020b1c', 'GRCh38', '', '',
             '36.1', 'BWA-MEM-2.3', '', '',
        ])
        self._assert_expected_file(read_file, expected_rows, absent_rows=absent_rows, additional_calls=1)

        expected_rows = [
            READ_SET_TABLE_HEADER,
            ['Broad_exome_VCGS_FAM203_621_D2', 'Broad_exome_VCGS_FAM203_621_D2_1'],
            ['Broad_exome_NA20888', 'Broad_exome_NA20888_1'],
        ]
        absent_rows = []
        (expected_rows if has_second_project else absent_rows).append(
            ['Broad_genome_NA20888_1', 'Broad_genome_NA20888_1_1']
        )
        self._assert_expected_file(read_set_file, expected_rows, absent_rows=absent_rows)

        self._assert_expected_file(called_file, [[
            'called_variants_dna_short_read_id', 'aligned_dna_short_read_set_id', 'called_variants_dna_file', 'md5sum',
            'caller_software', 'variant_types', 'analysis_details',
        ], [
            'SX2-3', 'Broad_exome_VCGS_FAM203_621_D2', 'gs://fc-fed09429-e563-44a7-aaeb-776c8336ba02/COL_FAM1_1_D1.SV.vcf',
            '129c28163df082', 'gatk4.1.2', 'SNV', 'DOI:10.5281/zenodo.4469317',
        ]])

        self._assert_expected_file(experiment_rna_file, [RNA_TABLE_HEADER, [
            'Broad_paired-end_NA19679', 'Broad_SM-N1P91', 'NA19679', 'Unknown', '151', 'paired-end', '2023-02-11',
            'NovaSeq', 'stranded poly-A pulldown', 'paired-end', 'LCSET-26942', '8.9818', '19480858', '106842386',
            '5.9', '80.2', '1.05', '', '', '', '', '',
        ]])

        self._assert_expected_file(aligned_rna_file, [[
            'aligned_rna_short_read_id', 'experiment_rna_short_read_id', 'aligned_rna_short_read_file',
            'aligned_rna_short_read_index_file', 'md5sum', 'reference_assembly', 'reference_assembly_uri',
            'reference_assembly_details', 'mean_coverage', 'gene_annotation', 'gene_annotation_details',
            'alignment_software', 'alignment_log_file', 'alignment_postprocessing', 'percent_uniquely_aligned',
            'percent_multimapped', 'percent_unaligned', 'quality_issues'
        ], [
            'Broad_paired-end_NA19679_1', 'Broad_paired-end_NA19679', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Aligned.out.crai', 'f6490b8ebdf2', 'GRCh38',
            'gs://gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta', '', '', 'GENCODEv26', '',
            'STARv2.7.10b', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/NA19679.Log.final.out', '', '80.53', '17.08',
            '1.71', ''
        ]])

        self._assert_expected_file(
            experiment_lookup_file,
            expected_rows=EXPERIMENT_LOOKUP_TABLE if has_second_project else EXPERIMENT_LOOKUP_TABLE[:4],
            absent_rows=None if has_second_project else EXPERIMENT_LOOKUP_TABLE[4:],
        )

        self._assert_expected_file(
            genetic_findings_file,
            expected_rows=GENETIC_FINDINGS_TABLE if has_second_project else GENETIC_FINDINGS_TABLE[:4],
            absent_rows=None,
        )

    def _assert_expected_file(self, actual_rows, expected_rows, additional_calls=0, absent_rows=None):
        self.assertEqual(len(actual_rows), len(expected_rows) + additional_calls)
        self.assertEqual(expected_rows[0], actual_rows[0])
        for row in expected_rows[1:]:
            self.assertIn(row, actual_rows)
        for row in absent_rows or []:
            self.assertNotIn(row, actual_rows)

    def _test_expected_gregor_airtable_calls(self, additional_samples=None, additional_mondo_ids=None):
        mondo_ids = ['0044970'] + (additional_mondo_ids or [])
        self.assertEqual(len(responses.calls), len(mondo_ids) + 5)
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
        sample_fields = ['CollaboratorSampleID', 'CollaboratorParticipantID', 'Recontactable', 'SMID']
        self.assert_expected_airtable_call(len(mondo_ids), f"OR({sample_filter})", sample_fields)
        sample_ids -= {'NA19675_1', 'NA19679', 'NA20888'}
        secondary_sample_filter = ','.join([f"{{SeqrCollaboratorSampleID}}='{sample_id}'" for sample_id in sorted(sample_ids)])
        sample_fields[0] = 'SeqrCollaboratorSampleID'
        self.assert_expected_airtable_call(len(mondo_ids) + 1, f"OR({secondary_sample_filter})", sample_fields)
        metadata_fields = [
            'CollaboratorParticipantID', '5prime3prime_bias_rna', 'CollaboratorSampleID_rna', 'CollaboratorSampleID_wes',
            'CollaboratorSampleID_wgs', 'Primary_Biosample_rna', 'RIN_rna', 'SMID_rna', 'SMID_wes', 'SMID_wgs',
            'aligned_dna_short_read_file_wes', 'aligned_dna_short_read_file_wgs', 'aligned_dna_short_read_index_file_wes',
            'aligned_dna_short_read_index_file_wgs',
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
            'target_insert_size_wgs', 'targeted_region_bed_file', 'targeted_regions_method_wes', 'tissue_affected_status_rna',
            'total_reads_rna', 'variant_types', 'within_site_batch_name_rna',
        ]
        self.assert_expected_airtable_call(
            len(mondo_ids) + 2, "OR(CollaboratorParticipantID='NA19675',CollaboratorParticipantID='NA19679',CollaboratorParticipantID='NA20888',CollaboratorParticipantID='VCGS_FAM203_621')",
            metadata_fields,
        )
        self.assert_expected_airtable_call(
            len(mondo_ids) + 3,"OR(RECORD_ID()='rec2B67GmXpAkQW8z')",['SMID'],
        )

        self.assertEqual(responses.calls[len(mondo_ids) + 4].request.url, MOCK_DATA_MODEL_URL)

    def test_family_metadata(self):
        url = reverse(family_metadata, args=['R0003_test'])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertListEqual(sorted([r['familyGuid'] for r in response_json['rows']]), ['F000011_11', 'F000012_12'])
        test_row = next(r for r in response_json['rows'] if r['familyGuid'] == 'F000012_12')
        self.assertDictEqual(test_row, {
            'projectGuid': 'R0003_test',
            'internal_project_id': 'Test Reprocessed Project',
            'familyGuid': 'F000012_12',
            'family_id': '12',
            'displayName': '12',
            'solve_status': 'Partially solved',
            'actual_inheritance': 'unknown',
            'condition_id': 'OMIM:616126',
            'condition_inheritance': 'Autosomal recessive',
            'known_condition_name': 'Immunodeficiency 38',
            'date_data_generation': '2017-02-05',
            'data_type': 'WES',
            'proband_id': 'NA20889',
            'maternal_id': '',
            'paternal_id': '',
            'other_individual_ids': 'NA20870; NA20888',
            'individual_count': 3,
            'family_structure': 'other',
            'genes': 'DEL:chr1:249045123-249045456; OR4G11P',
            'pmid_id': None,
            'phenotype_description': None,
            'analysisStatus': 'Q',
            'analysis_groups': '',
            'analysed_by': '',
            'consanguinity': 'Unknown',
        })

        # Test all projects
        all_projects_url = reverse(family_metadata, args=['all'])
        response = self.client.get(all_projects_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        expected_families = [
            'F000001_1', 'F000002_2', 'F000003_3', 'F000004_4', 'F000005_5', 'F000006_6', 'F000007_7', 'F000008_8',
            'F000009_9', 'F000010_10', 'F000011_11', 'F000012_12', 'F000013_13']
        self.assertListEqual(sorted([r['familyGuid'] for r in response_json['rows']]), expected_families)
        test_row = next(r for r in response_json['rows'] if r['familyGuid'] == 'F000001_1')
        self.assertDictEqual(test_row, {
            'projectGuid': 'R0001_1kg',
            'internal_project_id': '1kg project nåme with uniçøde',
            'familyGuid': 'F000001_1',
            'family_id': '1',
            'displayName': '1',
            'solve_status': 'Unsolved',
            'actual_inheritance': 'de novo',
            'date_data_generation': '2017-02-05',
            'data_type': 'WES',
            'proband_id': 'NA19675_1',
            'maternal_id': 'NA19679',
            'paternal_id': 'NA19678',
            'other_individual_ids': '',
            'individual_count': 3,
            'family_structure': 'trio',
            'genes': 'RP11',
            'pmid_id': '34415322',
            'phenotype_description': 'myopathy',
            'analysisStatus': 'Q',
            'analysis_groups': 'Test Group 1',
            'analysed_by': 'WES/WGS: Test No Access User (7/22/2022)',
            'consanguinity': 'Present',
            'condition_id': 'OMIM:615120',
            'known_condition_name': 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
            'condition_inheritance': 'Autosomal recessive|X-linked',
        })
        test_row = next(r for r in response_json['rows'] if r['familyGuid'] == 'F000003_3')
        self.assertDictEqual(test_row, {
            'projectGuid': 'R0001_1kg',
            'internal_project_id': '1kg project nåme with uniçøde',
            'familyGuid': 'F000003_3',
            'family_id': '3',
            'displayName': '3',
            'solve_status': 'Unsolved',
            'actual_inheritance': '',
            'date_data_generation': '2017-02-05',
            'data_type': 'WES',
            'other_individual_ids': 'NA20870',
            'individual_count': 1,
            'family_structure': 'singleton',
            'genes': '',
            'pmid_id': None,
            'phenotype_description': None,
            'analysisStatus': 'Q',
            'analysis_groups': 'Accepted; Test Group 1',
            'analysed_by': '',
            'consanguinity': 'Unknown',
            'condition_id': 'OMIM:615123',
            'known_condition_name': '',
            'condition_inheritance': 'Unknown',
        })

        # Test empty project
        empty_project_url = reverse(family_metadata, args=['R0002_empty'])
        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'rows': []})

        # Test access with no analyst group
        response = self.check_no_analyst_no_access(all_projects_url, has_override=self.HAS_PM_OVERRIDE)
        if self.HAS_PM_OVERRIDE:
            self.assertListEqual(
                sorted([r['familyGuid'] for r in response.json()['rows']]), expected_families + self.ADDITIONAL_FAMILIES)

    def test_variant_metadata(self):
        url = reverse(variant_metadata, args=[PROJECT_GUID])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        row_ids = ['NA19675_1_21_3343353', 'HG00731_1_248367227', 'HG00731_19_1912632']
        self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
        self.assertDictEqual(response_json['rows'][0], {
            **BASE_VARIANT_METADATA_ROW,
            'alt': 'G',
            'chrom': '21',
            'clinvar': {'alleleId': None, 'clinicalSignificance': '', 'goldStars': None, 'variationId': None},
            'condition_id': 'OMIM:615120',
            'condition_inheritance': 'Autosomal recessive|X-linked',
            'displayName': '1',
            'familyGuid': 'F000001_1',
            'family_id': '1',
            'gene_of_interest': 'RP11',
            'gene_id': 'ENSG00000135953',
            'gene_known_for_phenotype': 'Candidate',
            'genetic_findings_id': 'NA19675_1_21_3343353',
            'hgvsc': 'c.375_377delTCT',
            'hgvsp': 'p.Leu126del',
            'known_condition_name': 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
            'MME': True,
            'notes': 'This individual is published in PMID34415322',
            'participant_id': 'NA19675_1',
            'pos': 3343353,
            'projectGuid': 'R0001_1kg',
            'ref': 'GAGA',
            'seqr_chosen_consequence': 'inframe_deletion',
            'tags': ['Tier 1 - Novel gene and phenotype'],
            'transcript': 'ENST00000258436.5',
            'variant_inheritance': 'de novo',
            'variant_reference_assembly': 'GRCh37',
            'zygosity': 'Heterozygous',
        })
        expected_row = {
            **BASE_VARIANT_METADATA_ROW,
            'additional_family_members_with_variant': 'HG00732',
            'alt': 'T',
            'chrom': '1',
            'ClinGen_allele_ID': 'CA1501729',
            'clinvar': {'alleleId': None, 'clinicalSignificance': '', 'goldStars': None, 'variationId': None},
            'condition_id': 'MONDO:0044970',
            'condition_inheritance': 'Unknown',
            'displayName': '2',
            'familyGuid': 'F000002_2',
            'family_id': '2',
            'gene_of_interest': 'RP11',
            'gene_id': 'ENSG00000135953',
            'gene_known_for_phenotype': 'Known',
            'genetic_findings_id': 'HG00731_1_248367227',
            'known_condition_name': 'mitochondrial disease',
            'participant_id': 'HG00731',
            'phenotype_contribution': 'Uncertain',
            'pos': 248367227,
            'projectGuid': 'R0001_1kg',
            'ref': 'TC',
            'tags': ['Known gene for phenotype'],
            'variant_inheritance': 'paternal',
            'variant_reference_assembly': 'GRCh37',
            'zygosity': 'Homozygous',
        }
        self.assertDictEqual(response_json['rows'][1], expected_row)
        expected_mnv = {
            **BASE_VARIANT_METADATA_ROW,
            'alt': 'C',
            'chrom': '19',
            'condition_id': 'MONDO:0044970',
            'condition_inheritance': 'Unknown',
            'displayName': '2',
            'familyGuid': 'F000002_2',
            'family_id': '2',
            'gene_of_interest': 'OR4G11P',
            'gene_id': 'ENSG00000240361',
            'gene_known_for_phenotype': 'Known',
            'genetic_findings_id': 'HG00731_19_1912632',
            'hgvsc': 'c.586_587delinsTT',
            'hgvsp': 'p.Ala196Leu',
            'known_condition_name': 'mitochondrial disease',
            'notes': 'The following variants are part of the multinucleotide variant 19-1912632-G-C (c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T',
            'participant_id': 'HG00731',
            'pos': 1912632,
            'projectGuid': 'R0001_1kg',
            'ref': 'G',
            'tags': ['Known gene for phenotype'],
            'transcript': 'ENST00000371839',
            'variant_inheritance': 'unknown',
            'variant_reference_assembly': 'GRCh38',
            'variant_type': 'SNV',
            'zygosity': 'Heterozygous',
        }
        self.assertDictEqual(response_json['rows'][2], expected_mnv)

        # Test gregor projects
        gregor_projects_url = reverse(variant_metadata, args=['gregor'])
        response = self.client.get(gregor_projects_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        row_ids += ['NA20889_1_248367227', 'NA20889_1_249045487_DEL']
        self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
        self.assertDictEqual(response_json['rows'][1], expected_row)
        self.assertDictEqual(response_json['rows'][2], expected_mnv)
        self.assertDictEqual(response_json['rows'][3], {
            **BASE_VARIANT_METADATA_ROW,
            'MME': True,
            'alt': 'T',
            'chrom': '1',
            'ClinGen_allele_ID': 'CA1501729',
            'clinvar': {'alleleId': None, 'clinicalSignificance': '', 'goldStars': None, 'variationId': None},
            'condition_id': 'OMIM:616126',
            'condition_inheritance': 'Autosomal recessive',
            'displayName': '12',
            'familyGuid': 'F000012_12',
            'family_id': '12',
            'gene_of_interest': 'OR4G11P',
            'gene_id': 'ENSG00000240361',
            'gene_known_for_phenotype': 'Candidate',
            'genetic_findings_id': 'NA20889_1_248367227',
            'known_condition_name': 'Immunodeficiency 38',
            'hgvsc': 'c.3955G>A',
            'hgvsp': 'c.1586-17C>G',
            'participant_id': 'NA20889',
            'pos': 248367227,
            'partial_contribution_explained': 'HP:0000501|HP:0000365',
            'phenotype_contribution': 'Partial',
            'projectGuid': 'R0003_test',
            'internal_project_id': 'Test Reprocessed Project',
            'ref': 'TC',
            'seqr_chosen_consequence': 'intron_variant',
            'tags': ['Tier 1 - Novel gene and phenotype'],
            'transcript': 'ENST00000505820',
            'variant_inheritance': 'unknown',
            'variant_reference_assembly': 'GRCh37',
            'zygosity': 'Heterozygous',
        })
        self.assertDictEqual(response_json['rows'][4], {
            **BASE_VARIANT_METADATA_ROW,
            'alt': None,
            'chrom': '1',
            'condition_id': 'OMIM:616126',
            'condition_inheritance': 'Autosomal recessive',
            'known_condition_name': 'Immunodeficiency 38',
            'copy_number': 1,
            'displayName': '12',
            'pos_end': 249045898,
            'familyGuid': 'F000012_12',
            'family_id': '12',
            'gene_of_interest': 'OR4G11P',
            'gene_id': None,
            'gene_known_for_phenotype': 'Candidate',
            'genetic_findings_id': 'NA20889_1_249045487_DEL',
            'notes': 'Phasing incorrect in input VCF',
            'participant_id': 'NA20889',
            'pos': 249045487,
            'projectGuid': 'R0003_test',
            'internal_project_id': 'Test Reprocessed Project',
            'ref': None,
            'sv_type': 'DEL',
            'sv_name': 'DEL:chr1:249045487-249045898',
            'validated_name': 'DEL:chr1:249045123-249045456',
            'tags': ['Tier 1 - Novel gene and phenotype'],
            'variant_inheritance': 'unknown',
            'variant_reference_assembly': 'GRCh37',
            'variant_type': 'SV',
            'zygosity': 'Heterozygous',
        })

        # Test all projects
        all_projects_url = reverse(variant_metadata, args=['all'])
        response = self.client.get(all_projects_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
        self.assertDictEqual(response_json['rows'][1], expected_row)
        self.assertDictEqual(response_json['rows'][2], expected_mnv)

        # Test empty project
        empty_project_url = reverse(family_metadata, args=['R0002_empty'])
        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'rows': []})

        # Test access with no analyst group
        response = self.check_no_analyst_no_access(all_projects_url, has_override=self.HAS_PM_OVERRIDE)
        if self.HAS_PM_OVERRIDE:
            row_ids += self.ADDITIONAL_FINDINGS
            self.assertListEqual([r['genetic_findings_id'] for r in response.json()['rows']], row_ids)


class LocalReportAPITest(AuthenticationTestCase, ReportAPITest):

    fixtures = ['users', '1kg_project', 'reference_data', 'report_variants']
    ADDITIONAL_FAMILIES = ['F000014_14']
    ADDITIONAL_FINDINGS = ['NA21234_1_248367227']
    HAS_PM_OVERRIDE = True
    STATS_DATA = {
        'projectsCount': {'non_demo': 3, 'demo': 1},
        'familiesCount': {'non_demo': 12, 'demo': 2},
        'individualsCount': {'non_demo': 16, 'demo': 4},
        'sampleCountsByType': {
            'WES__SNV_INDEL': {'non_demo': 7},
            'WGS__SNV_INDEL': {'demo': 1},
            'WES__MITO': {'non_demo': 1},
            'WES__SV': {'non_demo': 3},
            'WGS__SV': {'non_demo': 1},
            'RNA__S': {'non_demo': 3},
            'RNA__T': {'non_demo': 2},
            'RNA__E': {'non_demo': 1},
        },
    }

    def _check_anvil_export_response(self, response, *args):
        self.assertEqual(response.status_code, 403)

    def _test_gregor_export(self, url, *args):
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)


class AnvilReportAPITest(AnvilAuthenticationTestCase, ReportAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'report_variants']
    HAS_PM_OVERRIDE = False
    STATS_DATA = {
        'projectsCount': {'internal': 1, 'external': 1, 'no_anvil': 1, 'demo': 1},
        'familiesCount': {'internal': 11, 'external': 1, 'no_anvil': 0, 'demo': 2},
        'individualsCount': {'internal': 14, 'external': 2, 'no_anvil': 0, 'demo': 4},
        'sampleCountsByType': {
            'WES__SNV_INDEL': {'internal': 7},
            'WGS__SNV_INDEL': {'demo': 1},
            'WES__MITO': {'internal': 1},
            'WES__SV': {'internal': 3},
            'WGS__SV': {'external': 1},
            'RNA__S': {'internal': 3},
            'RNA__T': {'internal': 2},
            'RNA__E': {'internal': 1},
        },
    }
