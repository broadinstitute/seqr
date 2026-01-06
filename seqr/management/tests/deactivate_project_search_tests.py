# -*- coding: utf-8 -*-
import mock
import responses

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError

from seqr.models import Sample, Project
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'
VARIANT_ID = '21-3343353-GAGA-G'


class ElasticsearchDeactivateProjectSearchTest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @responses.activate
    @mock.patch('seqr.management.commands.deactivate_project_search.input')
    def test_command(self, mock_input):
        mock_input.return_value = 'n'

        # Test invalid project
        with self.assertRaises(ObjectDoesNotExist):
            call_command('deactivate_project_search', 'foo')

        # Test user did not confirm.
        with self.assertRaises(CommandError) as e:
            call_command('deactivate_project_search', PROJECT_GUID)
        self.assertEqual(str(e.exception), 'Error: user did not confirm')

        # Test success
        Project.objects.filter(guid=PROJECT_GUID).update(genome_version='38')
        mock_input.return_value = 'y'
        self.reset_logs()
        self.maxDiff = None
        call_command('deactivate_project_search', PROJECT_GUID)
        self.assert_json_logs(user=None, expected=[
            ('update 11 Samples', {'dbUpdate': {
                'dbEntity': 'Sample',
                'entityIds': mock.ANY,
                'updateFields': ['is_active'],
                'updateType': 'bulk_update'},
            }),
            ('Deactivated 11 samples', None),
        ])

        active_samples = Sample.objects.filter(individual__family__project__guid=PROJECT_GUID, is_active=True)
        self.assertEqual(active_samples.count(), 0)

        # Re-running has no effect
        self.reset_logs()
        call_command('deactivate_project_search', PROJECT_GUID)
        self.assert_json_logs(user=None, expected=[('Deactivated 0 samples', None)])


class ClickhouseDeactivateProjectSearchTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_search']

    def test_command(self):
        with self.assertRaises(ValueError) as e:
            call_command('deactivate_project_search', 'foo')
        self.assertEqual(str(e.exception), 'handle is disabled without the elasticsearch backend')
