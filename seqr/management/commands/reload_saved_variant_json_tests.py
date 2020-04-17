#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase
from django.db.models.query_utils import Q
from seqr.models import Project

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
PROJECT_GUID2 = 'R0003_test'
SAVED_VARIANT_GUIDS = ['SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100']
FAMILY_ID = '1'

class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.variant_utils.update_project_saved_variant_json')
    def test_with_param_command(self, mock_update_json, mock_getLogger):
        mock_update_json.return_value = SAVED_VARIANT_GUIDS
        logger = mock_getLogger.return_value

        # Test with specific projects and a family id.
        call_command('reload_saved_variant_json',
                     PROJECT_NAME, PROJECT_GUID2,
                     '--family-id=1'.format(FAMILY_ID))

        projects_to_process = [PROJECT_NAME, PROJECT_GUID2]
        projects = Project.objects.filter(Q(name__in=projects_to_process) | Q(guid__in = projects_to_process))
        calls = [mock.call(project, family_id=FAMILY_ID) for project in projects]
        mock_update_json.assert_has_calls(calls, any_order = True)

        # Test for all projects and no specific family ids
        call_command('reload_saved_variant_json')

        projects = Project.objects.all()
        calls = [mock.call(project, family_id=None) for project in projects]
        mock_update_json.assert_has_calls(calls, any_order = True)

        # Test with an exception.
        mock_update_json.side_effect = Exception("Database error.")
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-id=1'.format(FAMILY_ID))

        projects_to_process = [PROJECT_GUID]
        projects = Project.objects.filter(Q(name__in=projects_to_process) | Q(guid__in = projects_to_process))
        calls = [mock.call(project, family_id=FAMILY_ID) for project in projects]
        mock_update_json.assert_has_calls(calls, any_order = True)

        loggerInfoCalls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 2 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Project: Test Project'),
            mock.call(u'Updated 2 variants for project Test Project'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 2 variants'),
            mock.call(u'  Test Project: Updated 2 variants'),
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
            mock.call(u'  Test Project: Updated 2 variants'),
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'1 failed projects'),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        logger.info.assert_has_calls(loggerInfoCalls)

        loggerErrorCalls = [
            mock.call(u'Error in project 1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        logger.error.assert_has_calls(loggerErrorCalls)
