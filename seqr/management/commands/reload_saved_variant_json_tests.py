#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase
from seqr.models import Project

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
SAVED_VARIANT_GUIDS = ['SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100']
FAMILY_ID = '1'


class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.variant_utils.update_project_saved_variant_json')
    def test_with_param_command(self, mock_update_json, mock_get_logger):
        mock_update_json.return_value = SAVED_VARIANT_GUIDS
        mock_logger = mock_get_logger.return_value

        # Test with a specific project and a family id.
        call_command('reload_saved_variant_json',
                     PROJECT_NAME,
                     '--family-id={}'.format(FAMILY_ID))

        project = Project.objects.get(name__exact = PROJECT_NAME)
        mock_update_json.assert_called_with(project, family_id=FAMILY_ID)

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 2 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 2 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_update_json.reset_mock()
        mock_logger.reset_mock()

        # Test for all projects and no specific family ids
        call_command('reload_saved_variant_json')

        projects = Project.objects.all()
        calls = [mock.call(project, family_id=None) for project in projects]
        mock_update_json.assert_has_calls(calls, any_order = True)

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 2 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Project: Empty Project'),
            mock.call(u'Updated 2 variants for project Empty Project'),
            mock.call(u'Project: Test Project'),
            mock.call(u'Updated 2 variants for project Test Project'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 2 variants'),
            mock.call(u'  Empty Project: Updated 2 variants'),
            mock.call(u'  Test Project: Updated 2 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_update_json.reset_mock()
        mock_logger.reset_mock()

        # Test with an exception.
        mock_update_json.side_effect = Exception("Database error.")
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-id={}'.format(FAMILY_ID))

        project = Project.objects.get(guid__exact = PROJECT_GUID)
        mock_update_json.assert_called_with(project, family_id=FAMILY_ID)

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'1 failed projects'),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)

        mock_logger.error.assert_called_with(u'Error in project 1kg project n\xe5me with uni\xe7\xf8de: Database error.')
