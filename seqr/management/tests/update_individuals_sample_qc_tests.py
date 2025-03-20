import json

import mock
from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from seqr.models import Individual

METADATA_JSON = {
    'callsets': ['1kg.vcf.gz', 'new_samples.vcf.gz'],
    'sample_type': 'WES',
    'family_samples': {
        'F000011_11': ['NA20885'],
        'F000012_12': ['NA20888', 'NA20889'],
        'F000014_14': ['NA21234'],
    },
    'failed_family_samples': {},
    'relatedness_check_file_path': '',
    'sample_qc': {
        'NA20885': {
            'filtered_callrate': 1.0,
            'contamination_rate': 5.0,
            'percent_bases_at_20x': 90.0,
            'mean_coverage': 28.0,
            'filter_flags': ['coverage'],
            'pca_scores': [0.1 for _ in range(20)],
            'prob_afr': 0.02,
            'prob_ami': 0.0,
            'prob_amr': 0.02,
            'prob_asj': 0.9,
            'prob_eas': 0.0,
            'prob_fin': 0.0,
            'prob_mid': 0.0,
            'prob_nfe': 0.05,
            'prob_sas': 0.01,
            **{f'pop_PC{i + 1}': 0.1 for i in range(20)},
            'qc_gen_anc': 'oth',
            'sample_qc.call_rate': 1.0,
            'sample_qc.n_called': 30,
            'sample_qc.n_not_called': 0,
            'sample_qc.n_filtered': 0,
            'sample_qc.n_hom_ref': 17,
            'sample_qc.n_het': 3,
            'sample_qc.n_hom_var': 10,
            'sample_qc.n_non_ref': 13,
            'sample_qc.n_singleton': 0,
            'sample_qc.n_snp': 23,
            'sample_qc.n_insertion': 0,
            'sample_qc.n_deletion': 0,
            'sample_qc.n_transition': 13,
            'sample_qc.n_transversion': 10,
            'sample_qc.n_star': 0,
            'sample_qc.r_ti_tv': 1.3,
            'sample_qc.r_het_hom_var': 0.3,
            'sample_qc.r_insertion_deletion': None,
            'sample_qc.f_inbreeding.f_stat': -0.038400752079048056,
            'sample_qc.f_inbreeding.n_called': 30,
            'sample_qc.f_inbreeding.expected_homs': 27.11094199999999,
            'sample_qc.f_inbreeding.observed_homs': 27,
            'fail_n_snp': True,
            'fail_r_ti_tv': False,
            'fail_r_insertion_deletion': None,
            'fail_n_insertion': True,
            'fail_n_deletion': True,
            'fail_r_het_hom_var': False,
            'fail_call_rate': False,
            'qc_metrics_filters': ['n_deletion', 'n_insertion', 'n_snp'],
        }
    }
}

class UpdateIndividualsSampleQC(TestCase):
    fixtures = ['users', '1kg_project']

    def setUp(self):
        patcher = mock.patch('seqr.management.commands.check_for_new_samples_from_pipeline.HAIL_SEARCH_DATA_DIR')
        mock_data_dir = patcher.start()
        mock_data_dir.__str__.return_value = 'gs://seqr-hail-search-data/v3.1'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_ls_process = mock.MagicMock()
        self.mock_metadata_file = mock.MagicMock()
        super().setUp()

    def test_command(self):
        # Test invalid dataset type
        with self.assertRaises(CommandError):
            call_command('update_individuals_sample_qc', 'MITO', 'GRCh38', 'manual__2025-02-24')

        # Test no runs
        self.mock_ls_process.communicate.return_value = b'\n', b''
        self.mock_subprocess.side_effect = [self.mock_ls_process]
        with self.assertRaises(CommandError):
            call_command('update_individuals_sample_qc', 'SNV_INDEL', 'GRCh38', 'manual__2025-02-24')

        # Test 'sample_qc' not in metadata
        self.mock_ls_process.communicate.return_value = b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-02-24/metadata.json\n', b''
        self.mock_metadata_file.stdout = [json.dumps({}).encode()]
        self.mock_subprocess.side_effect = [self.mock_ls_process, self.mock_metadata_file]

        with self.assertRaises(CommandError):
            call_command('update_individuals_sample_qc', 'SNV_INDEL', 'GRCh38', 'manual__2025-02-24')

        # Test valid case
        self.mock_metadata_file.stdout = [json.dumps(METADATA_JSON).encode()]
        self.mock_subprocess.side_effect = [self.mock_ls_process, self.mock_metadata_file]
        call_command('update_individuals_sample_qc', 'SNV_INDEL', 'GRCh38', 'manual__2025-02-24')

        # Individual model properly updated with sample qc results
        self.assertListEqual(
            list(Individual.objects.filter(
                guid__in=['I000015_na20885', 'I000016_na20888']).order_by('guid').values('filter_flags', 'pop_platform_filters', 'population')
             ),
            [{
                'filter_flags': {'coverage_exome': 90.0},
                'pop_platform_filters': {'n_deletion': 0, 'n_insertion': 0, 'n_snp': 23},
                'population': 'OTH'
            }, {
                'filter_flags': None,
                'pop_platform_filters': None,
                'population': 'SAS'
            }]
        )
