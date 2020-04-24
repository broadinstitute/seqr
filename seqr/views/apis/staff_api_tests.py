# -*- coding: utf-8 -*-
import mock
from datetime import datetime
import responses
from django.http import HttpResponse
from seqr.models import VariantTag, VariantTagType, SavedVariant

from settings import AIRTABLE_URL

from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.staff_api import elasticsearch_status, mme_details, seqr_stats, get_projects_for_category, discovery_sheet , success_story, anvil_export
from seqr.views.utils.test_utils import _check_login

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

EXPECTED_SUCCESS_STORY = {u'project_guid': u'R0001_1kg', u'family_guid': u'F000013_13', u'success_story_types': [u'A'], u'family_id': u'no_individuals', u'success_story': u'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', u'row_id': u'F000013_13'}

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 4,
    u'numberOfCases': 3,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 5,
    u'dateGenerated': datetime.now().strftime('%Y-%m-%d')
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
        "SeqrCollaboratorSampleID": "19F-DR-1",
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
        "SeqrCollaboratorSampleID": "19F-DR-2",
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
     'hpo_absent', 'phenotype_description', 'solve_state'],
    [
        {'project_guid': u'R0001_1kg', 'num_saved_variants': 1, 'dbgap_submission': 'No',
         'hpo_absent': u'HP:0011675|HP:0001674|HP:0001508', 'solve_state': 'Tier 1',
         'phenotype_group': '', 'sex': 'Male', 'phenotype_description': '', 'ancestry': '',
         'ancestry_detail': '', 'entity:subject_id': u'NA19675_1',
         'hpo_present': u'HP:0001631|HP:0002011|HP:0001636', 'multiple_datasets': 'No',
         'onset_category': u'Adult onset', 'subject_id': u'NA19675_1',
         'family_guid': u'F000001_1', 'affected_status': 'Affected', 'pmid_id': '',
         'project_id': u'1kg project n\xe5me with uni\xe7\xf8de'}
    ]
]
EXPECTED_PI_SAMPLE_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Sample',
    ['entity:sample_id', 'subject_id', 'sample_id', 'dbgap_sample_id', 'sample_source',
     'sample_provider', 'data_type', 'date_data_generation'],
    [
        {'entity:sample_id': u'NA19675_1', 'data_type': u'WES', 'subject_id': u'NA19675_1',
         'sample_provider': '', 'sample_id': u'NA19675', 'date_data_generation': '2017-02-05'}
    ]
]
EXPECTED_PI_FAMILY_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Family',
    ['entity:family_id', 'subject_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id',
     'family_relationship', 'consanguinity', 'consanguinity_detail', 'pedigree_image',
     'pedigree_detail', 'family_history', 'family_onset'],
    [
        {'maternal_id': u'NA19679', 'subject_id': u'NA19675_1', 'consanguinity': 'Present',
         'family_id': u'1', 'entity:family_id': u'NA19675_1', 'paternal_id': u'NA19678'}
    ]
]
EXPECTED_PI_DISCOVERY_FILE = [
    u'1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery',
    ['entity:discovery_id', 'subject_id', 'sample_id', 'Gene-1', 'Gene_Class-1',
     'inheritance_description-1', 'Zygosity-1', 'Chrom-1', 'Pos-1', 'Ref-1', 'Alt-1', 'hgvsc-1',
     'hgvsp-1', 'Transcript-1', 'sv_name-1', 'sv_type-1', 'significance-1'],
    [
        {'Zygosity-1': 'Heterozygous', 'Pos-1': '3343353', 'Ref-1': u'GAGA', 'Alt-1': u'G',
         'Gene-1': u'RP11-206L10.5', 'subject_id': u'NA19675_1', 'hgvsp-1': u'p.Leu126del',
         'Gene_Class-1': 'Known', 'Transcript-1': u'ENST00000258436',
         'hgvsc-1': u'c.375_377delTCT', 'sample_id': u'NA19675',
         'entity:discovery_id': u'NA19675_1', 'Chrom-1': u'2',
         'inheritance_description-1': 'de novo'}
    ]
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

    def test_mme_details(self):
        url = reverse(mme_details)
        _check_login(self, url)

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

    def test_discovery_sheet(self):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        _check_login(self, non_project_url)

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

        # Create a SavedVariant row needed by this test
        saved_variant = SavedVariant.objects.get(guid = "SV0000001_2103343353_r0390_100")
        variant_tag_type = VariantTagType.objects.get(name = "Known gene for phenotype")
        variant_tag = VariantTag.objects.create(variant_tag_type = variant_tag_type)
        variant_tag.saved_variants.add(saved_variant)
        variant_tag.save()

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

        self.assertListEqual([EXPECTED_PI_SUBJECT_FILE[0], EXPECTED_PI_SUBJECT_FILE[1]], [exported_files[0][0], exported_files[0][1]])
        self.assertListEqual([EXPECTED_PI_SAMPLE_FILE[0], EXPECTED_PI_SAMPLE_FILE[1]], [exported_files[1][0], exported_files[1][1]])
        self.assertListEqual([EXPECTED_PI_FAMILY_FILE[0], EXPECTED_PI_FAMILY_FILE[1]], [exported_files[2][0], exported_files[2][1]])
        self.assertListEqual([EXPECTED_PI_DISCOVERY_FILE[0], EXPECTED_PI_DISCOVERY_FILE[1]], [exported_files[3][0], exported_files[3][1]])
        self.assertIn(EXPECTED_PI_SUBJECT_FILE[2][0], exported_files[0][2])
        self.assertIn(EXPECTED_PI_SAMPLE_FILE[2][0], exported_files[1][2])
        self.assertIn(EXPECTED_PI_FAMILY_FILE[2][0], exported_files[2][2])
        self.assertIn(EXPECTED_PI_DISCOVERY_FILE[2][0], exported_files[3][2])
