import responses
from django.core.management import call_command
from django.test import TestCase
import mock

from seqr.models import Family, VariantTagType, VariantTag, Sample
from seqr.views.utils.test_utils import AirflowTestCase

MOCK_AIRFLOW_URL = 'http://testairflowserver'
DAG_NAME = 'DELETE_FAMILIES'


class TransferFamiliesTest(AirflowTestCase):
    fixtures = ['users', '1kg_project']
    LOADING_PROJECT_GUID = 'R0001_1kg'  # from-project

    def add_dag_tasks_response(self, projects):
        tasks = []
        for project in projects:
            tasks += [
                {'task_id': 'create_dataproc_cluster'},
                {'task_id': f'DeleteProjectFamilyTablesTask_{project}'},
            ]
        responses.add(responses.GET, f'{self._dag_url}/tasks', json={
            'tasks': tasks, 'total_entries': len(tasks),
        })

    def assert_airflow_calls(self, trigger_error=False, additional_tasks_check=False, dataset_type=None, offset=0, **kwargs):
        self.mock_airflow_logger.info.assert_not_called()

        call_count = 5
        if trigger_error:
            call_count = 1

        self.assertEqual(len(responses.calls), call_count)
        self.assertEqual(self.mock_authorized_session.call_count, call_count)
        dag_variables = {
            'projects_to_run': self.PROJECTS,
            'sample_type': 'WES',
            'dataset_type': 'SNV_INDEL',
            'reference_genome': 'GRCh37',
        }
        self._assert_airflow_calls(dag_variables, call_count, offset=offset)

    def _test_command(self, mock_logger, additional_family, logs):
        call_command(
            'transfer_families_to_different_project', '--from-project=R0001_1kg', '--to-project=R0003_test', additional_family, '2',
        )

        mock_logger.assert_has_calls([
            *logs,
            mock.call('Updating "Excluded" tags'),
            mock.call('Updating families'),
            mock.call('Done.'),
        ])

        family = Family.objects.get(family_id='2')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 3)

        old_tag_type = VariantTagType.objects.get(name='Excluded', project__guid='R0001_1kg')
        new_tag_type = VariantTagType.objects.get(name='Excluded', project__guid='R0003_test')
        self.assertNotEqual(old_tag_type, new_tag_type)
        self.assertEqual(old_tag_type.color, new_tag_type.color)
        self.assertEqual(old_tag_type.category, new_tag_type.category)
        self.assertEqual(VariantTag.objects.filter(variant_tag_type=old_tag_type).count(), 0)
        new_tags = VariantTag.objects.filter(variant_tag_type=new_tag_type)
        self.assertEqual(len(new_tags), 1)
        self.assertEqual(new_tags[0].saved_variants.first().family, family)

        return family
    #
    # @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    # @mock.patch('seqr.management.commands.transfer_families_to_different_project.logger.info')
    # def test_es_command(self, mock_logger):
    #     self._test_command(
    #         mock_logger, additional_family='12', logs=[mock.call('Found 1 out of 2 families. No match for: 12.')]
    #     )

    @responses.activate
    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', '')
    @mock.patch('seqr.management.commands.transfer_families_to_different_project.logger.info')
    def test_hail_backend_command(self, mock_logger):
        searchable_family = self._test_command(mock_logger, additional_family='4', logs=[
            mock.call('Found 2 out of 2 families.'),
            mock.call('Disabled search for 7 samples in the following 1 families: 2'),
        ])

        samples = Sample.objects.filter(individual__family=searchable_family)
        self.assertEqual(samples.count(), 7)
        self.assertEqual(samples.filter(is_active=True).count(), 0)

        family = Family.objects.get(family_id='4')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 1)

        self.assert_airflow_calls()
