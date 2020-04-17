#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
ELASTICSEARCH_INDEX = 'test_index'
INDEX_METADATA = {
                    "gencodeVersion": "25",
                    "hail_version": "0.2.24",
                    "genomeVersion": "38",
                    "sampleType": "WES",
                    "sourceFilePath": "test_index_alias_1_path.vcf.gz",
                }
SAMPLE_IDS = ["NA19679", "NA19675_1", "NA19678", "HG00731", "HG00732", "HG00732", "HG00733"]


class LiftProjectToHg38Test(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.dataset_utils.get_elasticsearch_index_samples')
    def test_command(self, mock_get_es_samples, mock_getLogger):
        logger = mock_getLogger.return_value
        mock_get_es_samples.return_value = SAMPLE_IDS, INDEX_METADATA
        call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index')
        ]
        logger.info.assert_has_calls(calls)
