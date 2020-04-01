# -*- coding: utf-8 -*-
import json
import mock

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

ES_CAT_INDICES=[{
    "index": "test_index",
    "docs.count": "122674997",
    "store.size": "14.9gb",
    "creation.date.string": "2019-11-04T19:33:47.522Z"
  },
  {
    "index": "test_index_second",
    "docs.count": "672312",
    "store.size": "233.4mb",
    "creation.date.string": "2019-10-03T19:53:53.846Z"
  },
  {
    "index": "test_index_old",
    "docs.count": "672312",
    "store.size": "233.4mb",
    "creation.date.string": "2019-10-03T19:53:53.846Z"
  },
  {
    "index": "1kg.vcf.gz",
    "docs.count": "672312",
    "store.size": "233.4mb",
    "creation.date.string": "2019-10-03T19:53:53.846Z"
  }]

ES_CAT_ALIAS=[
  {
    "alias": "010203d4c1452eef3f8725bfdee23476",
    "index": "test_index"
  },
  {
    "alias": "1531a081753f4a135eef25b3496316dd",
    "index": "1kg.vcf.gz"
  }]

TEST_INDEX_SRC_PATH="test_index_src_path"
TEST_INDEX_SECOND_SRC_PATH="test_index_second_src_path"
TEST_INDEX_OLD_SRC_PATH="test_index_old_src_path"
TEST_INDEX_1KG_SRC_PATH="test_index_1kg_src_path"
ES_INDEX_MAPPING={
  "test_index": {
    "mappings": {
      "variant": {
        "_meta": {
          "gencodeVersion": "25",
          "genomeVersion": "38",
          "sampleType_1": "WES",
          "sourceFilePath_1": "gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v13/RDG_Broad_WES_Internal.vcf.bgz",
          "genomeVersion_1": "38",
          "sampleType": "WES",
          "sourceFilePath": TEST_INDEX_SRC_PATH,
          "gencodeVersion_1": "25"
        },
        "_all": {
          "enabled": False
        }
      }
    }
  },
  "test_index_second": {
    "mappings": {
      "variant": {
        "_meta": {
          "gencodeVersion": "25",
          "hail_version": "0.2.24",
          "genomeVersion": "38",
          "sampleType_1": "WGS",
          "sourceFilePath_1": "gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal/v10/sharded_vcf/RDG_Broad_WGS_Internal.filtered.*.vcf.gz",
          "genomeVersion_1": "38",
          "sampleType": "WGS",
          "sourceFilePath": TEST_INDEX_SECOND_SRC_PATH,
          "hail_version_1": "0.2.24",
          "gencodeVersion_1": "25"
        },
        "_all": {
          "enabled": False
        },
      }
    }
  },
  "test_index_old": {
    "mappings": {
      "variant": {
        "_meta": {
          "gencodeVersion": "25",
          "hail_version": "0.2.24",
          "genomeVersion": "38",
          "sampleType_1": "WGS",
          "sourceFilePath_1": "gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal/v10/sharded_vcf/RDG_Broad_WGS_Internal.filtered.*.vcf.gz",
          "genomeVersion_1": "38",
          "sampleType": "WGS",
          "sourceFilePath": TEST_INDEX_SRC_PATH,
          "hail_version_1": "0.2.24",
          "gencodeVersion_1": "25"
        },
        "_all": {
          "enabled": False
        },
      }
    }
  },
  "1kg.vcf.gz": {
    "mappings": {
      "variant": {
        "_meta": {
          "gencodeVersion": "19",
          "genomeVersion": "37",
          "sampleType": "WES",
          "datasetType": "VARIANTS",
          "sourceFilePath": TEST_INDEX_1KG_SRC_PATH
        },
        "_all": {
          "enabled": False
        },
      }
    }
  }
}
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.staff_api import elasticsearch_status
from seqr.views.utils.test_utils import _check_login

class VariantSearchAPITest(TestCase):
    fixtures = ['users', '1kg_project']
    multi_db = True

    @mock.patch('elasticsearch_dsl.index.Index.get_mapping')
    @mock.patch('elasticsearch.client.cat.CatClient.aliases')
    @mock.patch('elasticsearch.client.cat.CatClient.indices')
    @mock.patch('elasticsearch.client.cat.CatClient.allocation')
    def test_elasticsearch_status(self, mock_cat_allocation, mock_cat_indices, mock_cat_aliases, mock_get_mapping):
        url = reverse(elasticsearch_status)
        _check_login(self, url)

        mock_cat_allocation.return_value = ES_CAT_ALLOCATION
        mock_cat_indices.return_value = ES_CAT_INDICES
        mock_cat_aliases.return_value = ES_CAT_ALIAS
        mock_get_mapping.return_value = ES_INDEX_MAPPING
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['indices', 'errors', 'diskStats', 'elasticsearchHost'])
        for index in response_json['indices']:
            index_id = index['index']
            mapping = ES_INDEX_MAPPING[index_id]
            self.assertEqual(index['sourceFilePath'], mapping['mappings']['variant']['_meta']['sourceFilePath'])
        node_list = []
        for node in response_json['diskStats']:
            node_list.append(node['node'])
        self.assertListEqual(node_list, ['node-1', 'UNASSIGNED'])

        mock_cat_allocation.assert_called_with(format="json",h="node,disk.avail,disk.used,disk.percent")
        mock_cat_indices.assert_called_with(format="json",h="index,docs.count,store.size,creation.date.string")
        mock_cat_aliases.assert_called_with(format="json",h="alias,index")
        mock_get_mapping.assert_called_with(doc_type='variant,structural_variant')
