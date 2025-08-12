import responses
from django.core.management import call_command
import mock

from seqr.models import Family, VariantTagType, VariantTag, Sample
from seqr.views.utils.test_utils import AirflowTestCase, AuthenticationTestCase


class TransferFamiliesTest(object):

    def _test_command(self, additional_family, logs):
        call_command(
            'transfer_families_to_different_project', '--from-project=R0001_1kg', '--to-project=R0003_test', additional_family, '2',
        )

        self.assert_json_logs(user=None, expected=[
            *logs,
            ('Updating "Excluded" tags', None),
            ('Updating families', None),
            ('Done.', None),
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


class TransferFamiliesLocalTest(TransferFamiliesTest, AuthenticationTestCase):
    fixtures = ['users', '1kg_project']


    def test_es_command(self):
        self._test_command(
            additional_family='12', logs=[('Found 1 out of 2 families. No match for: 12.', None)]
        )


class TransferFamiliesAirflowTest(TransferFamiliesTest, AirflowTestCase):
    fixtures = ['users', '1kg_project']
    PROJECT_GUID = 'R0001_1kg'  # from-project
    DAG_NAME = 'DELETE_FAMILIES'

    def setUp(self):
        super().setUp()
        self.set_up_one_dag(dataset_type='SNV_INDEL')
        self.set_up_one_dag(dataset_type='SV', status=400)

    def set_up_one_dag(self, **kwargs):
        dataset_type = kwargs.pop('dataset_type', 'MITO')
        super().set_up_one_dag(dataset_type=dataset_type, **kwargs)

    def _get_dag_variables(self, dataset_type, **kwargs):
        return {
            'projects_to_run': [self.PROJECT_GUID],
            'family_guids': ['F000002_2'],
            'reference_genome': 'GRCh37',
            'dataset_type': dataset_type
        }

    def _add_update_check_dag_responses(self, **kwargs):
        return self._add_check_dag_variable_responses(self._get_dag_variables(**kwargs), **kwargs)

    def assert_airflow_delete_families_calls(self):
        self._assert_call_counts(13)
        call_count_per_dag = 5
        offset = 0
        for dataset_type in ['MITO', 'SNV_INDEL']:
            self.assert_airflow_calls(self._get_dag_variables(dataset_type), call_count_per_dag, offset)
            offset += call_count_per_dag

        self._assert_update_variables_airflow_calls(self._get_dag_variables('SV'), offset)

    def _assert_update_check_airflow_calls(self, call_count, offset, update_check_path):
        variables_update_check_path = f'{self.MOCK_AIRFLOW_URL}/api/v1/variables/{self.DAG_NAME}'
        super()._assert_update_check_airflow_calls(call_count, offset, variables_update_check_path)

    @responses.activate
    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', '')
    def test_hail_backend_command(self):
        searchable_family = self._test_command(additional_family='4', logs=[
            ('Found 2 out of 2 families.', None),
            ('Disabled search for 7 samples in the following 1 families: 2', None),
            ('Successfully triggered DELETE_FAMILIES DAG for 1 MITO families', None),
            ('Successfully triggered DELETE_FAMILIES DAG for 1 SNV_INDEL families', None),
            ('400 Client Error: Bad Request for url: http://testairflowserver/api/v1/variables/DELETE_FAMILIES', {
                'severity': 'ERROR',
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
            })
        ])

        samples = Sample.objects.filter(individual__family=searchable_family)
        self.assertEqual(samples.count(), 7)
        self.assertEqual(samples.filter(is_active=True).count(), 0)

        family = Family.objects.get(family_id='4')
        self.assertEqual(family.project.guid, 'R0003_test')
        self.assertEqual(family.individual_set.count(), 1)

        self.assert_airflow_delete_families_calls()
