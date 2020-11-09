# -*- coding: utf-8 -*-
import mock
from django.utils.dateparse import parse_datetime
import pytz
from datetime import datetime
from requests import HTTPError
import responses
from settings import AIRTABLE_URL
import json

from django.urls.base import reverse

from seqr.views.apis.staff_api import elasticsearch_status, mme_details, seqr_stats, get_projects_for_category, discovery_sheet, success_story, anvil_export, sample_metadata_export, saved_variants_page, upload_qc_pipeline_output
from seqr.views.utils.test_utils import AuthenticationTestCase, urllib3_responses
from seqr.models import Individual


PROJECT_GUID = 'R0001_1kg'
NON_PROJECT_GUID ='NON_GUID'
PROJECT_EMPTY_GUID = 'R0002_empty'
COMPOUND_HET_PROJECT_GUID = 'R0003_test'

PROJECT_CATEGRORY_NAME = u'c\u00e5teg\u00f8ry with uni\u00e7\u00f8de'

ES_CAT_ALLOCATION=[{
    'node': 'node-1',
    'shards': '113',
    'disk.used': '67.2gb',
    'disk.avail': '188.6gb',
    'disk.percent': '26'
},
    {'node': 'UNASSIGNED',
     'shards': '2',
     'disk.used': None,
     'disk.avail': None,
     'disk.percent': None
     }]

EXPECTED_DISK_ALLOCATION = [{
    'node': 'node-1',
    'shards': '113',
    'diskUsed': '67.2gb',
    'diskAvail': '188.6gb',
    'diskPercent': '26'
},
    {'node': 'UNASSIGNED',
     'shards': '2',
     'diskUsed': None,
     'diskAvail': None,
     'diskPercent': None
     }]

ES_CAT_INDICES = [{
    "index": "test_index",
    "docs.count": "122674997",
    "store.size": "14.9gb",
    "creation.date.string": "2019-11-04T19:33:47.522Z"
},
    {
        "index": "test_index_alias_1",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_alias_2",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_no_project",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_sv",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
]

ES_CAT_ALIAS = [
    {
        "alias": "test_index_second",
        "index": "test_index_alias_1"
    },
    {
        "alias": "test_index_second",
        "index": "test_index_alias_2"
    }]

ES_INDEX_MAPPING = {
    "test_index": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "25",
                "genomeVersion": "38",
                "sampleType": "WES",
                "sourceFilePath": "test_index_file_path",
            },
            "_all": {
                "enabled": False
            }
        }
    },
    "test_index_alias_1": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "25",
                "hail_version": "0.2.24",
                "genomeVersion": "37",
                "sampleType": "WGS",
                "sourceFilePath": "test_index_alias_1_path",
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_alias_2": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WES",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_alias_2_path"
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_no_project": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WGS",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_no_project_path"
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_sv": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "29",
                "genomeVersion": "38",
                "sampleType": "WES",
                "datasetType": "SV",
                "sourceFilePath": "test_sv_index_path"
            },
        }
},
}

EXPECTED_SUCCESS_STORY = {'project_guid': 'R0001_1kg', 'family_guid': 'F000013_13', 'success_story_types': ['A'], 'family_id': 'no_individuals', 'success_story': 'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', 'row_id': 'F000013_13'}

TEST_INDEX_EXPECTED_DICT = {
    "index": "test_index",
    "sampleType": "WES",
    "genomeVersion": "38",
    "sourceFilePath": "test_index_file_path",
    "docsCount": "122674997",
    "storeSize": "14.9gb",
    "creationDateString": "2019-11-04T19:33:47.522Z",
    "gencodeVersion": "25",
    "projects": [{'projectName': '1kg project n\xe5me with uni\xe7\xf8de', 'projectGuid': 'R0001_1kg'}]
}

TEST_SV_INDEX_EXPECTED_DICT = {
    "index": "test_index_sv",
    "sampleType": "WES",
    "genomeVersion": "38",
    "sourceFilePath": "test_sv_index_path",
    "docsCount": "672312",
    "storeSize": "233.4mb",
    "creationDateString": "2019-10-03T19:53:53.846Z",
    "gencodeVersion": "29",
    "datasetType": "SV",
    "projects": [{'projectName': '1kg project n\xe5me with uni\xe7\xf8de', 'projectGuid': 'R0001_1kg'}]
}

TEST_INDEX_NO_PROJECT_EXPECTED_DICT = {
    "index": "test_index_no_project",
    "sampleType": "WGS",
    "genomeVersion": "37",
    "sourceFilePath": "test_index_no_project_path",
    "docsCount": "672312",
    "storeSize": "233.4mb",
    "creationDateString": "2019-10-03T19:53:53.846Z",
    "datasetType": "VARIANTS",
    "gencodeVersion": "19",
    "projects": []
}

TEST_INDEX_NO_PROJECT_EXPECTED_DICT = {
    "index": "test_index_no_project",
    "sampleType": "WGS",
    "genomeVersion": "37",
    "sourceFilePath": "test_index_no_project_path",
    "docsCount": "672312",
    "storeSize": "233.4mb",
    "creationDateString": "2019-10-03T19:53:53.846Z",
    "datasetType": "VARIANTS",
    "gencodeVersion": "19",
    "projects": []
}

EXPECTED_ERRORS = [
    'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)']

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 4,
    u'numberOfCases': 3,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 4,
    u'dateGenerated': '2020-04-27'
}

EXPECTED_DISCOVERY_SHEET_ROW = \
    {'project_guid': 'R0001_1kg', 'pubmed_ids': '', 'posted_publicly': '',
     'solved': 'TIER 1 GENE', 'head_or_neck': 'N', 'analysis_complete_status': 'complete',
     'cardiovascular_system': 'N', 'n_kindreds_overlapping_sv_similar_phenotype': '2',
     'biochemical_function': 'Y', 'omim_number_post_discovery': '615120,615123',
     'genome_wide_linkage': 'NA 2', 'metabolism_homeostasis': 'N', 'growth': 'N',
     't0': '2017-02-05T06:42:55.397Z', 'months_since_t0': 38, 'sample_source': 'CMG',
     'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
     'expected_inheritance_model': 'Autosomal recessive inheritance',
     'extras_variant_tag_list': ['21-3343353-GAGA-G  RP11-206L10.5  tier 1 - novel gene and phenotype'],
     'protein_interaction': 'N', 'n_kindreds': '1', 'num_individuals_sequenced': 3,
     'musculature': 'Y', 'sequencing_approach': 'WES', 'neoplasm': 'N',
     'collaborator': '1kg project n\xe5me with uni\xe7\xf8de',
     'actual_inheritance_model': 'de novo', 'novel_mendelian_gene': 'Y',
     'endocrine_system': 'N', 'patient_cells': 'N', 'komp_early_release': 'N',
     'connective_tissue': 'N', 'prenatal_development_or_birth': 'N', 'rescue': 'N',
     'family_guid': 'F000001_1', 'immune_system': 'N',
     'analysis_summary': '<b>\r\n                        F\xe5mily analysis summ\xe5ry.\r\n                    </b>',
     'gene_count': 'NA', 'gene_id': 'ENSG00000135953', 'abdomen': 'N', 'limbs': 'N',
     'blood': 'N', 'phenotype_class': 'KNOWN', 'submitted_to_mme': 'Y',
     'n_unrelated_kindreds_with_causal_variants_in_gene': '3',
     'row_id': 'F000001_1ENSG00000135953', 'eye_defects': 'N', 'omim_number_initial': '12345',
     'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'Y', 'ear_defects': 'N',
     'thoracic_cavity': 'N', 'non_patient_cell_model': 'N',
     't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped_1.png',
     'family_id': '1', 'genitourinary_system': 'N', 'coded_phenotype': '',
     'animal_model': 'N', 'non_human_cell_culture_model': 'N', 'expression': 'N',
     'gene_name': 'RP11-206L10.5', 'breast': 'N'}

EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW = {
    'project_guid': 'R0003_test', 'pubmed_ids': '', 'posted_publicly': '', 'solved': 'TIER 1 GENE', 'head_or_neck': 'N',
    'analysis_complete_status': 'complete', 'cardiovascular_system': 'Y',
    'n_kindreds_overlapping_sv_similar_phenotype': 'NA', 'biochemical_function': 'N', 'omim_number_post_discovery': 'NA',
    'genome_wide_linkage': 'NA', 'metabolism_homeostasis': 'N', 'growth': 'N', 't0': '2020-02-05T06:42:55.397Z',
    'months_since_t0': 2, 'sample_source': 'CMG', 'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
    'expected_inheritance_model': 'multiple', 'num_individuals_sequenced': 1, 'sequencing_approach': 'REAN',
    'extras_variant_tag_list': ['1-248367227-TC-T  OR4G11P  tier 1 - novel gene and phenotype',
        'prefix_19107_DEL  OR4G11P  tier 1 - novel gene and phenotype'], 'protein_interaction': 'N', 'n_kindreds': '1',
    'neoplasm': 'N', 'collaborator': 'Test Reprocessed Project', 'actual_inheritance_model': 'AR-comphet',
    'novel_mendelian_gene': 'Y', 'endocrine_system': 'N', 'komp_early_release': 'N', 'connective_tissue': 'N',
    'prenatal_development_or_birth': 'N', 'rescue': 'N', 'family_guid': 'F000011_11', 'immune_system': 'N',
    'analysis_summary': '', 'gene_count': 'NA', 'gene_id': 'ENSG00000240361', 'abdomen': 'N', 'limbs': 'N',
    'phenotype_class': 'New', 'submitted_to_mme': 'Y', 'n_unrelated_kindreds_with_causal_variants_in_gene': '1',
    'blood': 'N',  'row_id': 'F000011_11ENSG00000240361', 'eye_defects': 'N', 'omim_number_initial': 'NA',
    'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'N', 'ear_defects': 'N', 'thoracic_cavity': 'N',
    'non_patient_cell_model': 'N', 't0_copy': '2020-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped.png',
    'family_id': '11', 'genitourinary_system': 'N', 'coded_phenotype': '', 'animal_model': 'N', 'expression': 'N',
    'non_human_cell_culture_model': 'N', 'gene_name': 'OR4G11P', 'breast': 'N', 'musculature': 'N', 'patient_cells': 'N',}

AIRTABLE_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "NA19675",
        "CollaboratorSampleID": "VCGS_FAM203_621_D1",
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
        "CollaboratorSampleID": "VCGS_FAM203_621_D2",
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

PAGINATED_AIRTABLE_SAMPLE_RECORDS = {
    'offset': 'abc123',
    'records': [{
      'id': 'rec2B6OGmQpfuRW3s',
      'fields': {
        'CollaboratorSampleID': 'NA19675',
        'Collaborator': ['recW24C2CJW5lT64K'],
        'dbgap_study_id': 'dbgap_study_id_2',
        'dbgap_subject_id': 'dbgap_subject_id_1',
        'dbgap_sample_id': 'SM-A4GQ4',
        'SequencingProduct': [
          'Mendelian Rare Disease Exome'
        ],
        'dbgap_submission': [
          'WES',
          'Array'
        ]
      },
      'createdTime': '2019-09-09T19:21:12.000Z'
    }
]}

AIRTABLE_COLLABORATOR_RECORDS = {
    "records": [
        {
            "id": "recW24C2CJW5lT64K",
            "fields": {
                "CollaboratorID": "Hildebrandt",
            }
        },
        {
            "id": "reca4hcBnbA2cnZf9",
            "fields": {
                "CollaboratorID": "Seidman",
            }
        }
    ]
}

EXPECTED_SAMPLE_METADATA_ROW = {
    "project_guid": "R0003_test",
    "num_saved_variants": 2,
    "dbgap_submission": "No",
    "solve_state": "Tier 1",
    "sample_id": "NA20885",
    "Gene_Class-1": "Tier 1 - Candidate",
    "Gene_Class-2": "Tier 1 - Candidate",
    "sample_provider": "",
    "inheritance_description-1": "Autosomal recessive (compound heterozygous)",
    "inheritance_description-2": "Autosomal recessive (compound heterozygous)",
    "hpo_absent": "",
    "novel_mendelian_gene-1": "Y",
    "novel_mendelian_gene-2": "Y",
    "hgvsc-1": "c.3955G>A",
    "date_data_generation": "2020-02-05",
    "Zygosity-1": "Heterozygous",
    "Zygosity-2": "Heterozygous",
    "variant_genome_build-1": "GRCh37",
    "variant_genome_build-2": "GRCh37",
    "Ref-1": "TC",
    "sv_type-2": "Deletion",
    "sv_name-2": "DEL:chr12:49045487-49045898",
    "multiple_datasets": "No",
    "ancestry_detail": "Ashkenazi Jewish",
    "maternal_id": "",
    "paternal_id": "",
    "hgvsp-1": "c.1586-17C>G",
    "entity:family_id": "11",
    "entity:discovery_id": "NA20885",
    "project_id": "Test Reprocessed Project",
    "Pos-1": "248367227",
    "data_type": "WES",
    "family_guid": "F000011_11",
    "congenital_status": "Unknown",
    "hpo_present": "HP:0011675 (Arrhythmia)|HP:0001509 ()",
    "Transcript-1": "ENST00000505820",
    "ancestry": "Ashkenazi Jewish",
    "phenotype_group": "",
    "sex": "Male",
    "entity:subject_id": "NA20885",
    "entity:sample_id": "NA20885",
    "Chrom-1": "1",
    "Alt-1": "T",
    "Gene-1": "OR4G11P",
    "pmid_id": "",
    "phenotype_description": "",
    "affected_status": "Affected",
    "family_id": "11",
    "MME": "Y",
    "subject_id": "NA20885",
    "proband_relationship": "",
    "consanguinity": "None suspected",
    "sequencing_center": "Broad",
  }

SAMPLE_QC_DATA = [
    b'PCT_CONTAMINATION	AL_PCT_CHIMERAS	HS_PCT_TARGET_BASES_20X	seqr_id	data_type	filter_flags	qc_platform	qc_pop	pop_PC1	pop_PC2	pop_PC3	pop_PC4	pop_PC5	pop_PC6	qc_metrics_filters	sample_qc.call_rate	sample_qc.n_called	sample_qc.n_not_called	sample_qc.n_filtered	sample_qc.n_hom_ref	sample_qc.n_het	sample_qc.n_hom_var	sample_qc.n_non_ref	sample_qc.n_singleton	sample_qc.n_snp	sample_qc.n_insertion	sample_qc.n_deletion	sample_qc.n_transition	sample_qc.n_transversion	sample_qc.n_star	sample_qc.r_ti_tv	sample_qc.r_het_hom_var	sample_qc.r_insertion_deletion	sample_qc.f_inbreeding.f_stat	sample_qc.f_inbreeding.n_called	sample_qc.f_inbreeding.expected_homs	sample_qc.f_inbreeding.observed_homs\n',
    b'1.6E-01	5.567E-01	9.2619E+01	MANZ_1169_DNA	WES	[]	WES-010230 Standard Germline Exome	nfe	6.0654E-02	6.0452E-02	-6.2635E-03	-4.3252E-03	-2.1807E-02	-1.948E-02	["n_snp"]	7.1223E-01	14660344	5923237	0	14485322	114532	60490	175022	585	195114	18516	21882	133675	61439	0	2.1757E+00	1.8934E+00	8.4617E-01	5.3509E-01	14660344	1.4414E+07	14545812\n',
    b'NA	NA	NA	NA	WES	[]	Unknown	nfe	4.6581E-02	5.7881E-02	-5.6011E-03	3.5992E-03	-2.9438E-02	-9.6098E-03	["r_insertion_deletion"]	6.2631E-01	12891805	7691776	0	12743977	97831	49997	147828	237	165267	15474	17084	114154	51113	0	2.2334E+00	1.9567E+00	9.0576E-01	5.4467E-01	12891805	1.2677E+07	12793974\n',
    b'NA	NA	NA	NA19675_1	WES	[]	Unknown	amr	2.2367E-02	-1.9772E-02	6.3769E-02	2.5774E-03	-1.6655E-02	2.0457E-03	["r_ti_tv","n_deletion","n_snp","r_insertion_deletion","n_insertion"]	1.9959E-01	4108373	16475208	0	3998257	67927	42189	110116	18572	127706	13701	10898	82568	45138	0	1.8292E+00	1.6101E+00	1.2572E+00	5.3586E-02	4108373	4.0366E+06	4040446\n',
    b'5.6E-01	3.273E-01	8.1446E+01	NA19678	WES	["coverage"]	Standard Exome Sequencing v4	sas	2.4039E-02	-6.9517E-02	-4.1485E-02	1.421E-01	7.5583E-02	-2.0986E-02	["n_insertion"]	4.6084E-01	9485820	11097761	0	9379951	59871	45998	105869	736	136529	6857	8481	95247	41282	0	2.3072E+00	1.3016E+00	8.0851E-01	5.2126E-01	9485820	9.3608E+06	9425949\n',
    b'5.4E-01	5.0841E+00	8.7288E+01	HG00732	WES	["chimera"]	Standard Germline Exome v5	nfe	5.2785E-02	5.547E-02	-5.82E-03	2.7961E-02	-4.2259E-02	3.0271E-02	["n_insertion","r_insertion_deletion"]	6.8762E-01	14153622	6429959	0	13964844	123884	64894	188778	1719	202194	29507	21971	138470	63724	0	2.173E+00	1.909E+00	1.343E+00	4.924E-01	14153622	1.391E+07	14029738\n',
    b'2.79E+00	1.8996E+01	7.352E+01	HG00733	WES	["contamination","not_real_flag"]	Standard Germline Exome v5	oth	-1.5417E-01	2.8868E-02	-1.3819E-02	4.1915E-02	-4.0001E-02	7.6392E-02	["n_insertion","r_insertion_deletion", "not_real_filter"]	6.1147E-01	12586314	7997267	0	12383958	140784	61572	202356	8751	204812	38051	21065	140282	64530	0	2.1739E+00	2.2865E+00	1.8064E+00	3.6592E-01	12586314	1.2364E+07	12445530\n',
]

SAMPLE_QC_DATA_NO_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	n/a	[]	Standard Germline Exome v5	nfe	[]\n',
]

SAMPLE_QC_DATA_MORE_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	WES	[]	Standard Germline Exome v5	nfe	[]\n',
    b'03133B_3	WGS	[]	Standard Germline Exome v5	nfe	[]\n',
]


SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	UNKNOWN	[]	Standard Germline Exome v5	nfe	[]\n',
]

SAMPLE_SV_QC_DATA = [
    b'sample	lt100_raw_calls	lt10_highQS_rare_calls\n',
    b'RP-123_MANZ_1169_DNA_v1_Exome_GCP	FALSE	TRUE\n',
    b'RP-123_NA_v1_Exome_GCP	TRUE	FALSE\n',
    b'RP-123_NA19675_1_v1_Exome_GCP	TRUE	TRUE\n',
    b'RP-123_NA19678_v1_Exome_GCP	TRUE	FALSE\n',
    b'RP-123_HG00732_v1_Exome_GCP	FALSE	TRUE\n',
    b'RP-123_HG00733_v1_Exome_GCP	FALSE	FALSE\n',
]


class StaffAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    @urllib3_responses.activate
    def test_elasticsearch_status(self):
        url = reverse(elasticsearch_status)
        self.check_staff_login(url)

        urllib3_responses.add_json(
            '/_cat/allocation?format=json&h=node,shards,disk.avail,disk.used,disk.percent', ES_CAT_ALLOCATION)
        urllib3_responses.add_json(
           '/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string', ES_CAT_INDICES)
        urllib3_responses.add_json('/_cat/aliases?format=json&h=alias,index', ES_CAT_ALIAS)
        urllib3_responses.add_json('/_all/_mapping', ES_INDEX_MAPPING)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'indices', 'errors', 'diskStats', 'elasticsearchHost'})

        self.assertEqual(len(response_json['indices']), 5)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertListEqual(response_json['errors'], EXPECTED_ERRORS)

        self.assertListEqual(response_json['diskStats'], EXPECTED_DISK_ALLOCATION)


    @mock.patch('matchmaker.matchmaker_utils.datetime')
    def test_mme_details(self, mock_datetime):
        url = reverse(mme_details)
        self.check_staff_login(url)

        mock_datetime.now.return_value = datetime(2020, 4, 27, 20, 16, 1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'metrics', 'genesById', 'submissions'})
        self.assertDictEqual(response_json['metrics'], EXPECTED_MME_DETAILS_METRICS)
        self.assertEqual(len(response_json['genesById']), 4)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000233750', 'ENSG00000227232', 'ENSG00000223972', 'ENSG00000186092'})
        self.assertEqual(len(response_json['submissions']), 3)

    def test_seqr_stats(self):
        url = reverse(seqr_stats)
        self.check_staff_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualCount', 'familyCount', 'sampleCountByType'})
        self.assertEqual(response_json['individualCount'], 17)
        self.assertEqual(response_json['familyCount'], 13)
        self.assertDictEqual(response_json['sampleCountByType'], {'WES': 8})

    def test_get_projects_for_category(self):
        url = reverse(get_projects_for_category, args=[PROJECT_CATEGRORY_NAME])
        self.check_staff_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['projectGuids'])
        self.assertListEqual(response_json['projectGuids'], [PROJECT_GUID])

    @mock.patch('seqr.views.apis.staff_api.timezone')
    def test_discovery_sheet(self, mock_timezone):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        self.check_staff_login(non_project_url)

        mock_timezone.now.return_value = pytz.timezone("US/Eastern").localize(parse_datetime("2020-04-27 20:16:01"), is_dst=None)
        response = self.client.get(non_project_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid project {}'.format(NON_PROJECT_GUID))
        response_json = response.json()
        self.assertEqual(response_json['error'], 'Invalid project {}'.format(NON_PROJECT_GUID))

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
        self.assertListEqual(response_json['errors'], ['No data loaded for family: no_individuals. Skipping...'])
        self.assertEqual(len(response_json['rows']), 10)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_ROW, response_json['rows'])

        # test compound het reporting
        url = reverse(discovery_sheet, args=[COMPOUND_HET_PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], ['HPO category field not set for some HPO terms in 11'])
        self.assertEqual(len(response_json['rows']), 2)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW, response_json['rows'])

    def test_success_story(self):
        url = reverse(success_story, args=['all'])
        self.check_staff_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])

        self.assertEqual(len(response_json['rows']), 2)
        self.assertDictEqual(response_json['rows'][1], EXPECTED_SUCCESS_STORY)

        url = reverse(success_story, args=['A,T'])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])

        self.assertEqual(len(response_json['rows']), 1)
        self.assertDictEqual(response_json['rows'][0], EXPECTED_SUCCESS_STORY)

    @mock.patch('seqr.views.utils.export_utils.zipfile.ZipFile')
    @responses.activate
    def test_anvil_export(self, mock_zip):
        url = reverse(anvil_export, args=[PROJECT_GUID])
        self.check_staff_login(url)

        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), json=AIRTABLE_SAMPLE_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('content-disposition'),
            'attachment; filename="1kg project nme with unide_AnVIL_Metadata.zip"'
        )

        mock_write_zip = mock_zip.return_value.__enter__.return_value.writestr
        self.assertEqual(mock_write_zip.call_count, 4)
        mock_write_zip.assert_has_calls([
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Subject.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Sample.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Family.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery.tsv', mock.ANY),
        ])

        subject_file = mock_write_zip.call_args_list[0][0][1].split('\n')
        self.assertEqual(subject_file[0], '\t'.join([
            'entity:subject_id', '01-subject_id', '02-prior_testing', '03-project_id', '04-pmid_id',
            '05-dbgap_submission', '06-dbgap_study_id', '07-dbgap_subject_id', '08-multiple_datasets',
            '09-family_id', '10-paternal_id', '11-maternal_id', '12-twin_id', '13-proband_relationship', '14-sex',
            '15-ancestry', '16-ancestry_detail', '17-age_at_last_observation', '18-phenotype_group', '19-disease_id',
            '20-disease_description', '21-affected_status', '22-congenital_status', '23-age_of_onset', '24-hpo_present',
            '25-hpo_absent', '26-phenotype_description', '27-solve_state']))
        self.assertIn(u'\t'.join([
            'NA19675_1', 'NA19675_1', '-', u'1kg project nme with unide', '-', 'Yes', 'dbgap_stady_id_1',
            'dbgap_subject_id_1', 'No', '1', 'NA19678', 'NA19679', '-', 'Self', 'Male', '-', '-', '-', '-',
            'OMIM:615120;OMIM:615123', 'Myasthenic syndrome; congenital; 8; with pre- and postsynaptic defects;',
            'Affected', 'Adult onset', '-', 'HP:0001631|HP:0002011|HP:0001636', 'HP:0011675|HP:0001674|HP:0001508', '-',
            'Tier 1']), subject_file)

        sample_file = mock_write_zip.call_args_list[1][0][1].split('\n')
        self.assertEqual(sample_file[0], '\t'.join([
            'entity:sample_id', '01-subject_id', '02-sample_id', '03-dbgap_sample_id', '04-sequencing_center',
            '05-sample_source', '06-tissue_affected_status',]))
        self.assertIn(
            '\t'.join(['NA19675_1', 'NA19675_1', 'NA19675', 'SM-A4GQ4', 'Broad', '-', '-']),
            sample_file,
        )

        family_file = mock_write_zip.call_args_list[2][0][1].split('\n')
        self.assertEqual(family_file[0], '\t'.join([
            'entity:family_id', '01-family_id', '02-consanguinity', '03-consanguinity_detail', '04-pedigree_image',
            '05-pedigree_detail', '06-family_history', '07-family_onset']))
        self.assertIn('\t'.join([
            '1', '1', 'Present', '-', '-', '-', '-', '-',
        ]), family_file)

        discovery_file = mock_write_zip.call_args_list[3][0][1].split('\n')
        self.assertEqual(discovery_file[0], '\t'.join([
            'entity:discovery_id', '01-subject_id', '02-sample_id', '03-Gene', '04-Gene_Class',
            '05-inheritance_description', '06-Zygosity', '07-variant_genome_build', '08-Chrom', '09-Pos',
            '10-Ref', '11-Alt', '12-hgvsc', '13-hgvsp', '14-Transcript', '15-sv_name', '16-sv_type',
            '17-significance']))
        self.assertIn('\t'.join([
            'HG00731', 'HG00731', 'HG00731', 'RP11-206L10.5', 'Known', 'Autosomal recessive (homozygous)',
            'Homozygous', 'GRCh37', '1', '248367227', 'TC', 'T', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-']), discovery_file)
        self.assertIn('\t'.join([
            'NA19675_1', 'NA19675_1', 'NA19675', 'RP11-206L10.5', 'Tier 1 - Candidate', 'de novo',
            'Heterozygous', 'GRCh37', '21', '3343353', 'GAGA', 'G', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-']), discovery_file)

    @responses.activate
    def test_sample_metadata_export(self):
        url = reverse(sample_metadata_export, args=[COMPOUND_HET_PROJECT_GUID])
        self.check_staff_login(url)

        # Test invalid airtable responses
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), status=402)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 402)

        responses.reset()
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn(response.json()['error'], ['Unable to retrieve airtable data: No JSON object could be decoded',
                                        'Unable to retrieve airtable data: Expecting value: line 1 column 1 (char 0)'])

        responses.reset()
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=PAGINATED_AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Found multiple airtable records for sample NA19675 with mismatched values in field dbgap_study_id')
        self.assertEqual(len(responses.calls), 2)
        self.assertIsNone(responses.calls[0].request.params.get('offset'))
        self.assertEqual(responses.calls[1].request.params.get('offset'), 'abc123')

        # Test success
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertIn(EXPECTED_SAMPLE_METADATA_ROW, response_json['rows'])

    @mock.patch('seqr.views.apis.staff_api.MAX_SAVED_VARIANTS', 1)
    def test_saved_variants_page(self):
        url = reverse(saved_variants_page, args=['Tier 1 - Novel gene and phenotype'])
        self.check_staff_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Select a gene to filter variants')

        response = self.client.get('{}?gene=ENSG00000135953'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'projectsByGuid', 'locusListsByGuid', 'savedVariantsByGuid', 'variantFunctionalDataByGuid', 'genesById',
            'variantNotesByGuid', 'individualsByGuid', 'variantTagsByGuid', 'familiesByGuid'})
        expected_variant_guids = {
            'SV0000001_2103343353_r0390_100', 'SV0000007_prefix_19107_DEL_r00', 'SV0000006_1248367227_r0003_tes'}
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), expected_variant_guids)

        all_tag_url = reverse(saved_variants_page, args=['ALL'])
        response = self.client.get('{}?gene=ENSG00000135953'.format(all_tag_url))
        self.assertEqual(response.status_code, 200)
        expected_variant_guids.add('SV0000002_1248367227_r0390_100')
        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), expected_variant_guids)

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_upload_qc_pipeline_output(self, mock_subprocess):
        url = reverse(upload_qc_pipeline_output,)
        self.check_staff_login(url)

        request_data =json.dumps({
            'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'
        })

        # Test missing columns
        mock_subprocess.return_value.stdout = [b'', b'']
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.reason_phrase,
            'The following required columns are missing: seqr_id, data_type, filter_flags, qc_metrics_filters, qc_pop')

        # Test no data type error
        mock_subprocess.return_value.stdout = SAMPLE_QC_DATA_NO_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No data type detected')

        # Test multiple data types error
        mock_subprocess.return_value.stdout = SAMPLE_QC_DATA_MORE_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Multiple data types detected: wes ,wgs')

        # Test unexpected data type error
        mock_subprocess.return_value.stdout = SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Unexpected data type detected: "unknown" (should be "exome" or "genome")')

        # Test normal functions
        mock_subprocess.return_value.stdout = SAMPLE_QC_DATA
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
        self.assertListEqual(response_json['info'], [
            'Parsed 6 exome samples',
            'Found and updated matching seqr individuals for 4 samples'
        ])
        self.assertListEqual(response_json['warnings'], [
            'The following 1 samples were added to multiple individuals: NA19678 (2)',
            'The following 2 samples were skipped: MANZ_1169_DNA, NA',
            'The following filter flags have no known corresponding value and were not saved: not_real_flag',
            'The following population platform filters have no known corresponding value and were not saved: not_real_filter'
        ])

        indiv = Individual.objects.get(id = 1)
        self.assertIsNone(indiv.filter_flags)
        self.assertDictEqual(indiv.pop_platform_filters, {'n_deletion': '10898', 'n_snp': '127706', 'r_insertion_deletion': '1.2572E+00', 'r_ti_tv': '1.8292E+00', 'n_insertion': '13701'})
        self.assertEqual(indiv.population, 'AMR')

        indiv = Individual.objects.get(id = 2)
        self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
        self.assertEqual(indiv.population, 'SAS')

        indiv = Individual.objects.get(id=12)
        self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
        self.assertEqual(indiv.population, 'SAS')

        indiv = Individual.objects.get(id = 5)
        self.assertDictEqual(indiv.filter_flags, {'chimera': '5.0841E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '29507', 'r_insertion_deletion': '1.343E+00'})
        self.assertEqual(indiv.population, 'NFE')

        indiv = Individual.objects.get(id = 6)
        self.assertDictEqual(indiv.filter_flags, {'contamination': '2.79E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '38051', 'r_insertion_deletion': '1.8064E+00'})
        self.assertEqual(indiv.population, 'OTH')

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_upload_sv_qc(self, mock_subprocess):
        url = reverse(upload_qc_pipeline_output, )
        self.check_staff_login(url)

        request_data = json.dumps({
            'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/sv/sv_sample_metadata.tsv'
        })

        mock_subprocess.return_value.stdout = SAMPLE_SV_QC_DATA
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
        self.assertListEqual(response_json['info'], [
            'Parsed 6 SV samples',
            'Found and updated matching seqr individuals for 4 samples'
        ])
        self.assertListEqual(response_json['warnings'], ['The following 2 samples were skipped: MANZ_1169_DNA, NA'])

        self.assertIsNone(Individual.objects.get(individual_id='NA19675_1').sv_flags)
        self.assertListEqual(Individual.objects.get(individual_id='NA19678').sv_flags, ['high_QS_rare_calls:_>10'])
        self.assertListEqual(Individual.objects.get(individual_id='HG00732').sv_flags, ['raw_calls:_>100'])
        self.assertListEqual(
            Individual.objects.get(individual_id='HG00733').sv_flags,
            ['raw_calls:_>100', 'high_QS_rare_calls:_>10'])

    @mock.patch('seqr.views.apis.staff_api.KIBANA_ELASTICSEARCH_PASSWORD', 'abc123')
    @responses.activate
    def test_kibana_proxy(self):
        url = '/api/kibana/random/path'
        self.check_staff_login(url)

        response_args = {
            'stream': True,
            'body': 'Test response',
            'content_type': 'text/custom',
            'headers': {'x-test-header': 'test', 'keep-alive': 'true'},
        }
        proxy_url = 'http://localhost:5601{}'.format(url)
        responses.add(responses.GET, proxy_url, status=200, **response_args)
        responses.add(responses.POST, proxy_url, status=201, **response_args)
        responses.add(responses.GET, '{}/bad_response'.format(proxy_url), body=HTTPError())

        response = self.client.get(url, HTTP_TEST_HEADER='some/value')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Test response')
        self.assertEqual(response.get('content-type'), 'text/custom')
        self.assertEqual(response.get('x-test-header'), 'test')
        self.assertIsNone(response.get('keep-alive'))

        data = json.dumps({'content': 'Test Body'})
        response = self.client.post(url, content_type='application/json', data=data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(len(responses.calls), 2)

        get_request = responses.calls[0].request
        self.assertEqual(get_request.headers['Host'], 'localhost:5601')
        self.assertEqual(get_request.headers['Authorization'], 'Basic a2liYW5hOmFiYzEyMw==')
        self.assertEqual(get_request.headers['Test-Header'], 'some/value')

        post_request = responses.calls[1].request
        self.assertEqual(post_request.headers['Host'], 'localhost:5601')
        self.assertEqual(get_request.headers['Authorization'], 'Basic a2liYW5hOmFiYzEyMw==')
        self.assertEqual(post_request.headers['Content-Type'], 'application/json')
        self.assertEqual(post_request.headers['Content-Length'], '24')
        self.assertEqual(post_request.body, data.encode('utf-8'))

        # Test with error response
        response = self.client.get('{}/bad_response'.format(url))
        self.assertEqual(response.status_code, 500)

        # Test with connection error
        response = self.client.get('{}/bad_path'.format(url))
        self.assertContains(response, 'Error: Unable to connect to Kibana', status_code=400)
