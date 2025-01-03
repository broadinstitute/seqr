import json

import responses
from django.core.management import call_command
import mock

from seqr.models import Family, VariantTagType, VariantTag, Sample
from seqr.views.utils.test_utils import BaseAirflowTestCase

MOCK_AIRFLOW_URL = 'http://testairflowserver'
DAG_NAME = 'DELETE_FAMILIES'


class TransferFamiliesTest(BaseAirflowTestCase):
    fixtures = ['users', '1kg_project']
    LOADING_PROJECT_GUID = 'R0001_1kg'  # from-project

    DAG_VARIABLES = {
        'projects_to_run': [LOADING_PROJECT_GUID],
        'family_guids': ['F000002_2'],
        'reference_genome': 'GRCh37',
    }

    def setUp(self):
        self._dag_url = f'{MOCK_AIRFLOW_URL}/api/v1/dags/{DAG_NAME}'

        for dataset_type in ['MITO', 'SNV_INDEL', 'SV']:
            # check dag running state
            responses.add(responses.GET, f'{self._dag_url}/dagRuns', json={
                'dag_runs': [{'state': 'success'}]
            })
            # trigger dag
            responses.add(responses.POST, f'{self._dag_url}/dagRuns', json={})
            # update variables
            responses.add(
                responses.PATCH, f'{MOCK_AIRFLOW_URL}/api/v1/variables/{DAG_NAME}',
                json={'key': DAG_NAME, 'value': 'updated variables'},
            )
            # get variables
            responses.add(responses.GET, f'{self._dag_url}/variables', json={'variables': {}})
            # get variables again if the response of the previous request didn't include the updated variables
            responses.add(responses.GET, f'{self._dag_url}/variables', json={
                'variables': {**self.DAG_VARIABLES, 'dataset_type': dataset_type}
            })

        super().setUp()

    def assert_airflow_calls(self):
        self.assertEqual(self.mock_airflow_logger.info.call_count, 3)

        call_count = 15
        self.assertEqual(len(responses.calls), call_count)
        self.assertEqual(self.mock_authorized_session.call_count, call_count)

        dag_url = self._dag_url
        for dataset_type, offset in [('MITO', 0), ('SNV_INDEL', 5), ('SV', 10)]:
            # check dag running state
            self.assertEqual(responses.calls[offset].request.url, f'{dag_url}/dagRuns')
            self.assertEqual(responses.calls[offset].request.method, "GET")

            # update variables
            self.assertEqual(responses.calls[offset+1].request.url, f'{MOCK_AIRFLOW_URL}/api/v1/variables/{DAG_NAME}')
            self.assertEqual(responses.calls[offset+1].request.method, 'PATCH')
            self.assertDictEqual(json.loads(responses.calls[offset + 1].request.body), {
                'key': DAG_NAME,
                'value': json.dumps({**self.DAG_VARIABLES, 'dataset_type': dataset_type}),
            })

            # get variables
            self.assertEqual(responses.calls[offset+2].request.url, f'{dag_url}/variables')
            self.assertEqual(responses.calls[offset+2].request.method, 'GET')

            self.assertEqual(responses.calls[offset+3].request.url, f'{dag_url}/variables')
            self.assertEqual(responses.calls[offset+3].request.method, 'GET')

            # trigger dag
            self.assertEqual(responses.calls[offset+4].request.url, f'{dag_url}/dagRuns')
            self.assertEqual(responses.calls[offset+4].request.method, 'POST')
            self.assertDictEqual(json.loads(responses.calls[offset+4].request.body), {})

            self.mock_airflow_logger.warning.assert_not_called()
            self.mock_airflow_logger.error.assert_not_called()


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

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    @mock.patch('seqr.management.commands.transfer_families_to_different_project.logger.info')
    def test_es_command(self, mock_logger):
        self._test_command(
            mock_logger, additional_family='12', logs=[mock.call('Found 1 out of 2 families. No match for: 12.')]
        )

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
