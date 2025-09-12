# -*- coding: utf-8 -*-
import mock
import responses

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError

from clickhouse_search.models import EntriesSnvIndel, EntriesMito, EntriesGcnv, ProjectGtStatsSnvIndel, \
    ProjectGtStatsMito, AnnotationsSnvIndel, AnnotationsMito
from seqr.models import Sample, Project
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'
VARIANT_ID = '21-3343353-GAGA-G'


class DeactivateProjectSearchTest(object):

    DELETE_SUCCESS_LOGS = []

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
        ] + self.DELETE_SUCCESS_LOGS)

        active_samples = Sample.objects.filter(individual__family__project__guid=PROJECT_GUID, is_active=True)
        self.assertEqual(active_samples.count(), 0)
        self._assert_expected_delete()

        # Re-running has no effect
        self.reset_logs()
        call_command('deactivate_project_search', PROJECT_GUID)
        self.assert_json_logs(user=None, expected=[('Deactivated 0 samples', None)])

    def _assert_expected_delete(self):
        pass

class ElasticsearchDeactivateProjectSearchTest(AuthenticationTestCase, DeactivateProjectSearchTest):
    fixtures = ['users', '1kg_project']


class ClickhouseDeactivateProjectSearchTest(AnvilAuthenticationTestCase, DeactivateProjectSearchTest):
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_search']

    DELETE_SUCCESS_LOGS = [
        ('Deleted all MITO search data for project 1kg project nåme with uniçøde', None),
        ('Deleted all SNV_INDEL search data for project 1kg project nåme with uniçøde', None),
        ('Deleted all GCNV search data for project 1kg project nåme with uniçøde', None),
    ]

    def _assert_expected_delete(self):
        self.assertEqual(EntriesSnvIndel.objects.filter(project_guid=PROJECT_GUID).count(), 0)
        self.assertEqual(ProjectGtStatsSnvIndel.objects.filter(project_guid=PROJECT_GUID).count(), 0)
        self.assertEqual(EntriesMito.objects.filter(project_guid=PROJECT_GUID).count(), 0)
        self.assertEqual(ProjectGtStatsMito.objects.filter(project_guid=PROJECT_GUID).count(), 0)
        self.assertEqual(EntriesGcnv.objects.filter(project_guid=PROJECT_GUID).count(), 0)

        updated_seqr_pops_by_key = dict(AnnotationsSnvIndel.objects.all().join_seqr_pop().values_list('key', 'seqrPop'))
        self.assertDictEqual(updated_seqr_pops_by_key, {
            1: (2, 2, 1, 1),
            2: (1, 1, 0, 0),
            3: (0, 0, 0, 0),
            4: (0, 0, 0, 0),
            5: (1, 1, 0, 0),
            6: (0, 0, 0, 0),
            22: (0, 3, 0, 1),
        })

        updated_mito_pops_by_key = dict(AnnotationsMito.objects.all().join_seqr_pop().values_list('key', 'seqrPop'))
        self.assertDictEqual(updated_mito_pops_by_key, {
            6: (0, 0, 0, 0),
            7: (0, 0, 0, 0),
            8: (0, 0, 0, 0),
        })
