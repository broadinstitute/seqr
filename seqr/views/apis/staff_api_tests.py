# -*- coding: utf-8 -*-
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.staff_api import elasticsearch_status, mme_details, seqr_stats, get_projects_for_category, discovery_sheet , success_story
from seqr.views.utils.test_utils import _check_login

PROJECT_GUID = 'R0001_1kg'
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

EXPECTED_ERRORS = [
    u'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)']


class StaffAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data', 'variant_searches']
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

    def test_seqr_stats(self):
        url = reverse(seqr_stats)
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['individualCount', 'familyCount', 'sampleCountByType'])

    def test_get_projects_for_category(self):
        url = reverse(get_projects_for_category, args=[PROJECT_CATEGRORY_NAME])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['projectGuids'])

    def test_discovery_sheet(self):
        url = reverse(discovery_sheet, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows', 'errors'])

    def test_success_story(self):
        url = reverse(success_story, args=['all'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['rows'])
