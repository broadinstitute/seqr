# -*- coding: utf-8 -*-
import mock
from django.utils.dateparse import parse_datetime
import pytz
from datetime import datetime
import responses
from django.http import HttpResponse
from settings import AIRTABLE_URL
import json

from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.staff_api import elasticsearch_status, mme_details, seqr_stats, get_projects_for_category, discovery_sheet, success_story, anvil_export, sample_metadata_export, saved_variants_page, upload_qc_pipeline_output
from seqr.views.utils.test_utils import _check_login
from seqr.models import Individual

PROJECT_GUID = 'R0001_1kg'
NON_PROJECT_GUID ='NON_GUID'
PROJECT_EMPTY_GUID = 'R0002_empty'

PROJECT_CATEGRORY_NAME = 'test category name'

ES_CAT_ALLOCATION=[{
    u'node': u'node-1',
    u'disk.used': u'67.2gb',
    u'disk.avail': u'188.6gb',
    u'disk.percent': u'26'
},
    {u'node': u'UNASSIGNED',
     u'disk.used': None,
     u'disk.avail': None,
     u'disk.percent': None
     }]

EXPECTED_DISK_ALLOCATION = [{
    u'node': u'node-1',
    u'diskUsed': u'67.2gb',
    u'diskAvail': u'188.6gb',
    u'diskPercent': u'26'
},
    {u'node': u'UNASSIGNED',
     u'diskUsed': None,
     u'diskAvail': None,
     u'diskPercent': None
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
            "variant": {
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
        }
    },
    "test_index_alias_1": {
        "mappings": {
            "variant": {
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
        }
    },
    "test_index_alias_2": {
        "mappings": {
            "variant": {
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
        }
    },
    "test_index_no_project": {
        "mappings": {
            "variant": {
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
        }
    },
    "test_index_sv": {
        "mappings": {
            "structural_variant": {
                "_meta": {
                    "gencodeVersion": "29",
                    "genomeVersion": "38",
                    "sampleType": "WES",
                    "datasetType": "SV",
                    "sourceFilePath": "test_sv_index_path"
                },
            }
        }
    },
}

EXPECTED_SUCCESS_STORY = {u'project_guid': u'R0001_1kg', u'family_guid': u'F000013_13', u'success_story_types': [u'A'], u'family_id': u'no_individuals', u'success_story': u'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', u'row_id': u'F000013_13'}

TEST_INDEX_EXPECTED_DICT = {
    "index": "test_index",
    "sampleType": "WES",
    "genomeVersion": "38",
    "sourceFilePath": "test_index_file_path",
    "docsCount": "122674997",
    "storeSize": "14.9gb",
    "creationDateString": "2019-11-04T19:33:47.522Z",
    "gencodeVersion": "25",
    "docType": "variant",
    "projects": [{u'projectName': u'1kg project n\xe5me with uni\xe7\xf8de', u'projectGuid': u'R0001_1kg'}]
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
    "docType": "structural_variant",
    "datasetType": "SV",
    "projects": [{u'projectName': u'1kg project n\xe5me with uni\xe7\xf8de', u'projectGuid': u'R0001_1kg'}]
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
    "docType": "variant",
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
    "docType": "variant",
    "projects": []
}

EXPECTED_ERRORS = [
    u'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)']

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 4,
    u'numberOfCases': 3,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 5,
    u'dateGenerated': '2020-04-27'
}

EXPECTED_DISCOVERY_SHEET_ROW = \
    {u'project_guid': u'R0001_1kg', u'pubmed_ids': u'', u'posted_publicly': u'',
     u'solved': u'TIER 1 GENE', u'head_or_neck': u'N', u'analysis_complete_status': u'complete',
     u'cardiovascular_system': u'Y', u'n_kindreds_overlapping_sv_similar_phenotype': u'NA',
     u'biochemical_function': u'Y', u'omim_number_post_discovery': u'NA',
     u'genome_wide_linkage': u'NA 2', u'metabolism_homeostasis': u'N', u'growth': u'N',
     u't0': u'2017-02-05T06:42:55.397Z', u'months_since_t0': 38, u'sample_source': u'CMG',
     u'integument': u'N', u'voice': u'N', u'skeletal_system': u'N',
     u'expected_inheritance_model': u'multiple',
     u'extras_variant_tag_list': [u'21-3343353-GAGA-G  RP11-206L10.5  tier 1 - novel gene and phenotype'],
     u'protein_interaction': u'N', u'n_kindreds': u'1', u'num_individuals_sequenced': 3,
     u'musculature': u'N', u'sequencing_approach': u'WES', u'neoplasm': u'N',
     u'collaborator': u'1kg project n\xe5me with uni\xe7\xf8de',
     u'actual_inheritance_model': u'de novo', u'novel_mendelian_gene': u'Y',
     u'endocrine_system': u'N', u'patient_cells': u'N', u'komp_early_release': u'N',
     u'connective_tissue': u'N', u'prenatal_development_or_birth': u'N', u'rescue': u'N',
     u'family_guid': u'F000001_1', u'immune_system': u'N',
     u'analysis_summary': u'<b>\r\n                        F\xe5mily analysis summ\xe5ry.\r\n                    </b>',
     u'gene_count': u'NA', u'gene_id': u'ENSG00000135953', u'abdomen': u'N', u'limbs': u'N',
     u'blood': u'N', u'phenotype_class': u'New', u'submitted_to_mme': u'Y',
     u'n_unrelated_kindreds_with_causal_variants_in_gene': u'1',
     u'row_id': u'F000001_1ENSG00000135953', u'eye_defects': u'N', u'omim_number_initial': u'NA',
     u'p_value': u'NA', u'respiratory': u'N', u'nervous_system': u'Y', u'ear_defects': u'N',
     u'thoracic_cavity': u'N', u'non_patient_cell_model': u'N',
     u't0_copy': u'2017-02-05T06:42:55.397Z', u'extras_pedigree_url': u'/media/ped_1.png',
     u'family_id': u'1', u'genitourinary_system': u'N', u'coded_phenotype': u'',
     u'animal_model': u'N', u'non_human_cell_culture_model': u'N', u'expression': u'N',
     u'gene_name': u'RP11-206L10.5', u'breast': u'N'}

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

EXPECTED_PI_SUBJECT_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Subject',
    ['entity:subject_id', 'subject_id', 'prior_testing', 'project_id', 'pmid_id',
     'dbgap_submission', 'dbgap_study_id', 'dbgap_subject_id', 'multiple_datasets', 'sex',
     'ancestry', 'ancestry_detail', 'age_at_last_observation', 'phenotype_group', 'disease_id',
     'disease_description', 'affected_status', 'onset_category', 'age_of_onset', 'hpo_present',
     'hpo_absent', 'phenotype_description', 'solve_state']
]
EXPECTED_PI_SUBJECT_ROW = {
    'project_guid': u'R0001_1kg', 'num_saved_variants': 0, 'dbgap_submission': 'Yes',
    'hpo_absent': u'HP:0011675|HP:0001674|HP:0001508', 'solve_state': 'Unsolved', 'phenotype_group': '',
    'sex': 'Male', 'phenotype_description': '', 'ancestry': '', 'ancestry_detail': '',
    'entity:subject_id': u'NA19675_1', 'dbgap_subject_id': u'dbgap_subject_id_1',
    'hpo_present': u'HP:0001631|HP:0002011|HP:0001636', 'dbgap_study_id': u'dbgap_stady_id_1',
    'multiple_datasets': 'No', 'onset_category': u'Adult onset', 'subject_id': u'NA19675_1',
    'family_guid': u'F000001_1', 'affected_status': 'Affected', 'pmid_id': '',
    'project_id': u'1kg project n\xe5me with uni\xe7\xf8de'}

EXPECTED_PI_SAMPLE_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Sample',
    ['entity:sample_id', 'subject_id', 'sample_id', 'dbgap_sample_id', 'sample_source',
     'sample_provider', 'data_type', 'date_data_generation']
]
EXPECTED_PI_SAMPLE_ROW = {
    'entity:sample_id': u'NA19675_1', 'data_type': u'WES', 'subject_id': u'NA19675_1',
    'sample_provider': u'Hildebrandt', 'dbgap_sample_id': u'SM-A4GQ4', 'sample_id': u'NA19675',
    'date_data_generation': '2017-02-05'}

EXPECTED_PI_FAMILY_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Family',
    ['entity:family_id', 'subject_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id',
     'family_relationship', 'consanguinity', 'consanguinity_detail', 'pedigree_image',
     'pedigree_detail', 'family_history', 'family_onset']
]
EXPECTED_PI_FAMILY_ROW = {
    'maternal_id': u'NA19679', 'subject_id': u'NA19675_1', 'consanguinity': 'Present',
    'family_id': u'1', 'entity:family_id': u'NA19675_1', 'paternal_id': u'NA19678'}

EXPECTED_PI_DISCOVERY_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery',
    ['entity:discovery_id', 'subject_id', 'sample_id', 'Gene-1', 'Gene_Class-1',
     'inheritance_description-1', 'Zygosity-1', 'Chrom-1', 'Pos-1', 'Ref-1', 'Alt-1', 'hgvsc-1',
     'hgvsp-1', 'Transcript-1', 'sv_name-1', 'sv_type-1', 'significance-1']
]
EXPECTED_PI_DISCOVERY_ROW = {
    'Zygosity-1': 'Heterozygous', 'Pos-1': '248367227', 'Ref-1': u'TC', 'Alt-1': u'T',
    'Gene-1': u'RP11-206L10.5', 'subject_id': u'HG00731', 'hgvsp-1': u'p.Leu126del',
    'Gene_Class-1': 'Known', 'Transcript-1': u'ENST00000258436',
    'hgvsc-1': u'c.375_377delTCT', 'sample_id': u'HG00731',
    'entity:discovery_id': u'HG00731', 'Chrom-1': u'1',
    'inheritance_description-1': 'de novo'}

EXPECTED_SAMPLE_METADATA_ROW = {
    "project_guid": "R0001_1kg",
    "num_saved_variants": 1,
    "dbgap_submission": "Yes",
    "solve_state": "Tier 1",
    "sample_id": "NA19675",
    "Gene_Class-1": "Known",
    "sample_provider": "Hildebrandt",
    "inheritance_description-1": "de novo",
    "hpo_present": "HP:0001631 (Defect in the atrial septum)|HP:0002011 (Morphological abnormality of the central nervous system)|HP:0001636 (Tetralogy of Fallot)",
    "novel_mendelian_gene-1": "Y",
    "hgvsc-1": "c.375_377delTCT",
    "date_data_generation": "2017-02-05",
    "dbgap_subject_id": "dbgap_subject_id_1",
    "Zygosity-1": "Heterozygous",
    "dbgap_study_id": "dbgap_stady_id_1",
    "Ref-1": "GAGA",
    "multiple_datasets": "No",
    "ancestry_detail": "",
    "maternal_id": "NA19679",
    "paternal_id": "NA19678",
    "hgvsp-1": "p.Leu126del",
    "entity:family_id": "NA19675_1",
    "entity:discovery_id": "NA19675_1",
    "project_id": u"1kg project n\xe5me with uni\xe7\xf8de",
    "Pos-1": "3343353",
    "data_type": "WES",
    "family_guid": "F000001_1",
    "onset_category": "Adult onset",
    "hpo_absent": "HP:0011675 (Arrhythmia)|HP:0001674 (Complete atrioventricular canal defect)|HP:0001508 (Failure to thrive)",
    "Transcript-1": "ENST00000258436",
    "dbgap_sample_id": "SM-A4GQ4",
    "ancestry": "",
    "phenotype_group": "",
    "sex": "Male",
    "entity:subject_id": "NA19675_1",
    "entity:sample_id": "NA19675_1",
    "Chrom-1": "21",
    "Alt-1": "G",
    "Gene-1": "RP11-206L10.5",
    "pmid_id": "",
    "consanguinity": "Present",
    "phenotype_description": "",
    "affected_status": "Affected",
    "family_id": "1",
    "MME": "Y",
    "subject_id": "NA19675_1"
  }

SAMPLE_QC_DATA = [
    'PCT_CONTAMINATION	AL_PCT_CHIMERAS	HS_PCT_TARGET_BASES_20X	seqr_id	data_type	filter_flags	qc_platform	qc_pop	pop_PC1	pop_PC2	pop_PC3	pop_PC4	pop_PC5	pop_PC6	qc_metrics_filters	sample_qc.call_rate	sample_qc.n_called	sample_qc.n_not_called	sample_qc.n_filtered	sample_qc.n_hom_ref	sample_qc.n_het	sample_qc.n_hom_var	sample_qc.n_non_ref	sample_qc.n_singleton	sample_qc.n_snp	sample_qc.n_insertion	sample_qc.n_deletion	sample_qc.n_transition	sample_qc.n_transversion	sample_qc.n_star	sample_qc.r_ti_tv	sample_qc.r_het_hom_var	sample_qc.r_insertion_deletion	sample_qc.f_inbreeding.f_stat	sample_qc.f_inbreeding.n_called	sample_qc.f_inbreeding.expected_homs	sample_qc.f_inbreeding.observed_homs\n',
    '1.6E-01	5.567E-01	9.2619E+01	MANZ_1169_DNA	WES	[]	WES-010230 Standard Germline Exome	nfe	6.0654E-02	6.0452E-02	-6.2635E-03	-4.3252E-03	-2.1807E-02	-1.948E-02	["n_snp"]	7.1223E-01	14660344	5923237	0	14485322	114532	60490	175022	585	195114	18516	21882	133675	61439	0	2.1757E+00	1.8934E+00	8.4617E-01	5.3509E-01	14660344	1.4414E+07	14545812\n',
    'NA	NA	NA	NA	WES	[]	Unknown	nfe	4.6581E-02	5.7881E-02	-5.6011E-03	3.5992E-03	-2.9438E-02	-9.6098E-03	["r_insertion_deletion"]	6.2631E-01	12891805	7691776	0	12743977	97831	49997	147828	237	165267	15474	17084	114154	51113	0	2.2334E+00	1.9567E+00	9.0576E-01	5.4467E-01	12891805	1.2677E+07	12793974\n',
    'NA	NA	NA	NA19675	WES	[]	Unknown	amr	2.2367E-02	-1.9772E-02	6.3769E-02	2.5774E-03	-1.6655E-02	2.0457E-03	["r_ti_tv","n_deletion","n_snp","r_insertion_deletion","n_insertion"]	1.9959E-01	4108373	16475208	0	3998257	67927	42189	110116	18572	127706	13701	10898	82568	45138	0	1.8292E+00	1.6101E+00	1.2572E+00	5.3586E-02	4108373	4.0366E+06	4040446\n',
    '5.6E-01	3.273E-01	8.1446E+01	NA19678	WES	["coverage"]	Standard Exome Sequencing v4	sas	2.4039E-02	-6.9517E-02	-4.1485E-02	1.421E-01	7.5583E-02	-2.0986E-02	["n_insertion"]	4.6084E-01	9485820	11097761	0	9379951	59871	45998	105869	736	136529	6857	8481	95247	41282	0	2.3072E+00	1.3016E+00	8.0851E-01	5.2126E-01	9485820	9.3608E+06	9425949\n',
    '5.4E-01	5.0841E+00	8.7288E+01	HG00732	WES	["chimera"]	Standard Germline Exome v5	nfe	5.2785E-02	5.547E-02	-5.82E-03	2.7961E-02	-4.2259E-02	3.0271E-02	["n_insertion","r_insertion_deletion"]	6.8762E-01	14153622	6429959	0	13964844	123884	64894	188778	1719	202194	29507	21971	138470	63724	0	2.173E+00	1.909E+00	1.343E+00	4.924E-01	14153622	1.391E+07	14029738\n',
    '2.79E+00	1.8996E+01	7.352E+01	HG00733	WES	["contamination","not_real_flag"]	Standard Germline Exome v5	oth	-1.5417E-01	2.8868E-02	-1.3819E-02	4.1915E-02	-4.0001E-02	7.6392E-02	["n_insertion","r_insertion_deletion", "not_real_filter"]	6.1147E-01	12586314	7997267	0	12383958	140784	61572	202356	8751	204812	38051	21065	140282	64530	0	2.1739E+00	2.2865E+00	1.8064E+00	3.6592E-01	12586314	1.2364E+07	12445530\n',
]

SAMPLE_QC_DATA_NO_DATA_TYPE = [
    'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    '03133B_2	n/a	[]	Standard Germline Exome v5	nfe	[]\n',
]

SAMPLE_QC_DATA_MORE_DATA_TYPE = [
    'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    '03133B_2	WES	[]	Standard Germline Exome v5	nfe	[]\n',
    '03133B_3	WGS	[]	Standard Germline Exome v5	nfe	[]\n',
]


SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE = [
    'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    '03133B_2	UNKNOWN	[]	Standard Germline Exome v5	nfe	[]\n',
]


class StaffAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    @mock.patch('elasticsearch_dsl.index.Index.get_mapping')
    @mock.patch('elasticsearch.Elasticsearch')
    def test_elasticsearch_status(self, mock_elasticsearch, mock_get_mapping):
        url = reverse(elasticsearch_status)
        _check_login(self, url)

        mock_es_client = mock_elasticsearch.return_value
        mock_es_client.cat.allocation.return_value = ES_CAT_ALLOCATION
        mock_es_client.cat.indices.return_value = ES_CAT_INDICES
        mock_es_client.cat.aliases.return_value = ES_CAT_ALIAS
        mock_get_mapping.return_value = ES_INDEX_MAPPING
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['indices', 'errors', 'diskStats', 'elasticsearchHost'])

        self.assertEqual(len(response_json['indices']), 5)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertListEqual(response_json['errors'], EXPECTED_ERRORS)

        self.assertListEqual(response_json['diskStats'], EXPECTED_DISK_ALLOCATION)

        mock_es_client.cat.allocation.assert_called_with(format="json", h="node,disk.avail,disk.used,disk.percent")
        mock_es_client.cat.indices.assert_called_with(format="json",
                                                      h="index,docs.count,store.size,creation.date.string")
        mock_es_client.cat.aliases.assert_called_with(format="json", h="alias,index")
        mock_get_mapping.assert_called_with(doc_type='variant,structural_variant')

    @mock.patch('matchmaker.matchmaker_utils.datetime')
    def test_mme_details(self, mock_datetime):
        url = reverse(mme_details)
        _check_login(self, url)

        mock_datetime.now.return_value = datetime(2020, 4, 27, 20, 16, 01)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['metrics', 'genesById', 'submissions'])
        self.assertDictEqual(response_json['metrics'], EXPECTED_MME_DETAILS_METRICS)
        self.assertEqual(len(response_json['genesById']), 4)
        self.assertListEqual(response_json['genesById'].keys(), ['ENSG00000233750', 'ENSG00000227232', 'ENSG00000223972', 'ENSG00000186092'])
        self.assertEqual(len(response_json['submissions']), 3)

    def test_seqr_stats(self):
        url = reverse(seqr_stats)
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['individualCount', 'familyCount', 'sampleCountByType'])
        self.assertEqual(response_json['individualCount'], 16)
        self.assertEqual(response_json['familyCount'], 13)
        self.assertDictEqual(response_json['sampleCountByType'], {'WES': 8})

    def test_get_projects_for_category(self):
        url = reverse(get_projects_for_category, args=[PROJECT_CATEGRORY_NAME])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['projectGuids'])
        self.assertListEqual(response_json['projectGuids'], [PROJECT_GUID])

    @mock.patch('seqr.views.apis.staff_api.timezone')
    def test_discovery_sheet(self, mock_timezone):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        _check_login(self, non_project_url)

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
        self.assertListEqual(response_json.keys(), ['rows', 'errors'])
        self.assertListEqual(response_json['rows'], [])
        self.assertListEqual(response_json['errors'], ["No data loaded for project: Empty Project"])

        url = reverse(discovery_sheet, args=[PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows', 'errors'])
        self.assertListEqual(response_json['errors'], [u'No data loaded for family: no_individuals. Skipping...'])
        self.assertEqual(len(response_json['rows']), 10)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_ROW, response_json['rows'])

    def test_success_story(self):
        url = reverse(success_story, args=['all'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows'])

        self.assertEqual(len(response_json['rows']), 2)
        self.assertDictEqual(response_json['rows'][1], EXPECTED_SUCCESS_STORY)

        url = reverse(success_story, args=['A,T'])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows'])

        self.assertEqual(len(response_json['rows']), 1)
        self.assertDictEqual(response_json['rows'][0], EXPECTED_SUCCESS_STORY)

    @mock.patch('seqr.views.apis.staff_api.export_multiple_files')
    @responses.activate
    def test_anvil_export(self, mock_export_multiple_files):
        url = reverse(anvil_export, args=[PROJECT_GUID])
        _check_login(self, url)

        # We will test the inputs of the export_multiple_files method.
        # Outputs of the method are not important for this test but an HttpResponse data is still required by the API.
        mock_export_multiple_files.return_value = HttpResponse("Dummy text", content_type="text/plain")

        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        mock_export_multiple_files.assert_called_with(mock.ANY,
            u'1kg project n\u00e5me with uni\u00e7\u00f8de_AnVIL_Metadata',
            add_header_prefix = True, file_format = 'tsv', blank_value = '-')

        exported_files = mock_export_multiple_files.call_args.args[0]

        self.assertListEqual(EXPECTED_PI_SUBJECT_FILE, exported_files[0][:2])
        self.assertListEqual(EXPECTED_PI_SAMPLE_FILE, exported_files[1][:2])
        self.assertListEqual(EXPECTED_PI_FAMILY_FILE, exported_files[2][:2])
        self.assertListEqual(EXPECTED_PI_DISCOVERY_FILE, exported_files[3][:2])
        self.assertIn(EXPECTED_PI_SUBJECT_ROW, exported_files[0][2])
        self.assertIn(EXPECTED_PI_SAMPLE_ROW, exported_files[1][2])
        self.assertIn(EXPECTED_PI_FAMILY_ROW, exported_files[2][2])
        self.assertIn(EXPECTED_PI_DISCOVERY_ROW, exported_files[3][2])

    @responses.activate
    def test_sample_metadata_export(self):
        url = reverse(sample_metadata_export, args=[PROJECT_GUID])
        _check_login(self, url)

        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows'])
        self.assertIn(EXPECTED_SAMPLE_METADATA_ROW, response_json['rows'])

    def test_saved_variants_page(self):
        url = reverse(saved_variants_page, args=['Tier 1 - Novel gene and phenotype'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'locusListsByGuid', 'savedVariantsByGuid', 'variantFunctionalDataByGuid', 'genesById', 'variantNotesByGuid', 'individualsByGuid', 'variantTagsByGuid', 'familiesByGuid'])

    @mock.patch('seqr.views.apis.staff_api.file_iter')
    def test_upload_qc_pipeline_output(self, mock_file_iter):
        url = reverse(upload_qc_pipeline_output,)
        _check_login(self, url)

        # Test no dataset type error
        mock_file_iter.return_value = SAMPLE_QC_DATA_NO_DATA_TYPE
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No dataset type detected')

        # Test multiple dataset types error
        mock_file_iter.return_value = SAMPLE_QC_DATA_MORE_DATA_TYPE
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Multiple dataset types detected: wes ,wgs')

        # Test unexpected data type error
        mock_file_iter.return_value = SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Unexpected dataset type detected: "unknown" (should be "exome" or "genome")')

        # Test normal functions
        mock_file_iter.return_value = SAMPLE_QC_DATA
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['info', 'errors', 'warnings'])
        self.assertListEqual(response_json['info'], [
            u'Parsed 6 exome samples',
            u'Found and updated matching seqr individuals for 4 samples'
        ])
        self.assertListEqual(response_json['warnings'], [
            u'The following 2 samples were skipped: MANZ_1169_DNA, NA',
            u'The following filter flags have no known corresponding value and were not saved: not_real_flag',
            u'The following population platform filters have no known corresponding value and were not saved: not_real_filter'
        ])

        indiv = Individual.objects.get(id = 1)
        self.assertIsNone(indiv.filter_flags)
        self.assertDictEqual(indiv.pop_platform_filters, {u'n_deletion': '10898', u'n_snp': '127706', u'r_insertion_deletion': '1.2572E+00', u'r_ti_tv': '1.8292E+00', u'n_insertion': '13701'})
        self.assertEqual(indiv.population, 'AMR')

        indiv = Individual.objects.get(id = 2)
        self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
        self.assertDictEqual(indiv.pop_platform_filters, {u'n_insertion': '6857'})
        self.assertEqual(indiv.population, 'SAS')

        indiv = Individual.objects.get(id = 5)
        self.assertDictEqual(indiv.filter_flags, {u'chimera': '5.0841E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {u'n_insertion': '29507', u'r_insertion_deletion': '1.343E+00'})
        self.assertEqual(indiv.population, 'NFE')

        indiv = Individual.objects.get(id = 6)
        self.assertDictEqual(indiv.filter_flags, {u'contamination': u'2.79E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {u'n_insertion': '38051', u'r_insertion_deletion': '1.8064E+00'})
        self.assertEqual(indiv.population, 'OTH')

    @responses.activate
    def test_kibana_proxy(self):
        url = '/api/kibana/random/path'
        _check_login(self, url)

        response_args = {
            'stream': True,
            'body': 'Test response',
            'content_type': 'text/custom',
            'headers': {'x-test-header': 'test', 'keep-alive': 'true'},
        }
        proxy_url = 'http://localhost:5601{}'.format(url)
        responses.add(responses.GET, proxy_url, status=200, **response_args)
        responses.add(responses.POST, proxy_url, status=201, **response_args)

        response = self.client.get(url, HTTP_TEST_HEADER='some/value')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Test response')
        self.assertEqual(response.get('content-type'), 'text/custom')
        self.assertEqual(response.get('x-test-header'), 'test')
        self.assertIsNone(response.get('keep-alive'))

        data = json.dumps({'content': 'Test Body'})
        response = self.client.post(url, content_type='application/json', data=data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(len(responses.calls), 2)

        get_request = responses.calls[0].request
        self.assertEqual(get_request.headers['Host'], 'localhost:5601')
        self.assertEqual(get_request.headers['Test-Header'], 'some/value')

        post_request = responses.calls[1].request
        self.assertEqual(post_request.headers['Host'], 'localhost:5601')
        self.assertEqual(post_request.headers['Content-Type'], 'application/json')
        self.assertEqual(post_request.headers['Content-Length'], '24')
        self.assertEqual(post_request.body, data)

        # Test with connection error
        response = self.client.get('{}/bad_path'.format(url))
        self.assertContains(response, 'Error: Unable to connect to Kibana')
        self.assertEqual(response.status_code, 400)
