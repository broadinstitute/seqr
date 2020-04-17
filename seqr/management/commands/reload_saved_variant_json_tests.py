#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = '1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
PROJECT_GUID2 = 'R0002_empty'
SAVED_VARIANT_GUIDS = ['SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100']


class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.variant_utils.update_project_saved_variant_json')
    def test_normal_command(self, mock_update_json, mock_getLogger):
        logger = mock_getLogger.return_value
        mock_update_json.return_value = SAVED_VARIANT_GUIDS
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-id=1')

        calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 2 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 2 variants'),
        ]
        logger.info.assert_has_calls(calls)
