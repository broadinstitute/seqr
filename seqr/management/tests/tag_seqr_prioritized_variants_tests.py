from datetime import datetime
from django.core.management import call_command
import json
import mock

from clickhouse_search.search_tests import ClickhouseSearchTestCase
from clickhouse_search.test_utils import VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT3, GCNV_VARIANT4
from seqr.models import SavedVariant, VariantTag

PROJECT_GUID = 'R0001_1kg'

SNV_INDEL_MATCHES = {
    'Clinvar Pathogenic': (0, None),
    'Clinvar Pathogenic - Compound Heterozygous': (0, None),
    'Clinvar Both Pathogenic - Compound Heterozygous': (0, None),
    'Clinvar Pathogenic - Recessive': (1, None),
    'Clinvar Pathogenic - X-Linked Recessive': (0, 2),
    'Compound Heterozygous': (1, None),
    'Compound Heterozygous - Confirmed': (0, 1),
    'Compound Heterozygous - Both High Splice AI': (0, 1),
    'Compound Heterozygous - Both High Splice AI - Confirmed': (0, 1),
    'Compound Heterozygous - Clinvar Pathogenic/ High Splice AI': (0, None),
    'Compound Heterozygous - High Splice AI': (0, 1),
    'Compound Heterozygous - High Splice AI - Confirmed': (0, 1),
    'De Novo/ Dominant - Confirmed': (0, 1),
    'De Novo/ Dominant - Non-coding Transcript Exon Variant': (0, 1),
    'De Novo/ Dominant': (0, None),
    'High Splice AI - De Novo/ Dominant': (0, 1),
    'High Splice AI - De Novo/ Dominant Confirmed': (0, 1),
    'High Splice AI - Recessive': (0, 1),
    'High Splice AI - Recessive Confirmed': (0, 1),
    'High Splice AI - X-Linked Recessive': (0, 1),
    'High Splice AI - X-Linked Recessive Confirmed': (0, 0),
    'Recessive': (1, None),
    'X-Linked Recessive': (0, 2),
}
SV_MATCHES = {
    'SV - Compound Heterozygous': (1, None),
    'SV - De Novo/ Dominant': (0, None),
    'SV - Recessive': (1, None),
    'SV - X-Linked Recessive': (0, 0),
}
MITO_MATCHES = {
    'Mitochondrial - Pathogenic': (1, None),
    'Mitochondrial - De Novo/ Dominant': (1, None),
}
# TODO counts 0/1/0/1
MULTI_TYPE_MATCHES = {
    'Compound Heterozygous - One SV': (1, None),
    'Compound Heterozygous - Clinvar Pathogenic/ SV': (2, None),
    'Compound Heterozygous - High Splice AI/ SV': (1, None),
    'Compound Heterozygous - One SV - Confirmed': (2, None),
}

class CheckNewSamplesTest(ClickhouseSearchTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'panelapp', 'clickhouse_search', 'clickhouse_transcripts']

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    @mock.patch('seqr.utils.communication_utils._post_to_slack')
    @mock.patch('seqr.management.commands.tag_seqr_prioritized_variants.datetime')
    def test_command(self, mock_datetime, mock_slack, mock_email):
        mock_datetime.now.return_value = datetime(2025, 11, 15)

        call_command('tag_seqr_prioritized_variants', PROJECT_GUID)

        self._assert_expected_logs(num_new=6, creation_stats={
            'SNV_INDEL': {'num_variants': 3, 'tag_id_range': (1726986, 1726988)},
            'SV': {'num_variants': 2, 'tag_id_range': (1726988, 1726990)},
            'MITO': {'num_variants': 2, 'tag_id_range': (1726990, 1726992)},
            'MULTI': {'tag_id_range': (1726992, 1726993)},
        })

        new_saved_variants = SavedVariant.objects.filter(key__in=[2, 3, 4, 18, 19]).order_by('key').values(
            'key', 'variant_id', 'family_id', 'dataset_type', 'xpos', 'xpos_end', 'ref', 'alt', 'gene_ids', 'genotypes', 'saved_variant_json',
        )
        self.assertListEqual(list(new_saved_variants),  [{
            'key': 2, 'variant_id': '1-38724419-T-G', 'family_id': 2, 'dataset_type': 'SNV_INDEL', 'xpos': 1038724419,
            'xpos_end': 1038724419, 'ref': 'T', 'alt': 'G', 'gene_ids': ['ENSG00000177000', 'ENSG00000277258'],
            'genotypes': VARIANT2['genotypes'], 'saved_variant_json': {},
        }, {'key': 3, 'variant_id': '1-91502721-G-A', 'family_id': 2, 'dataset_type': 'SNV_INDEL', 'xpos': 1091502721,
            'xpos_end': 1091502721, 'ref': 'G', 'alt': 'A', 'gene_ids': ['ENSG00000097046', 'ENSG00000177000'],
            'genotypes': VARIANT3['genotypes'], 'saved_variant_json': {},
        }, {'key': 4, 'variant_id': '1-91511686-T-G', 'family_id': 2, 'dataset_type': 'SNV_INDEL', 'xpos': 1091511686,
            'xpos_end': 1091511686, 'ref': 'T', 'alt': 'G', 'gene_ids': ['ENSG00000097046'],
            'genotypes': VARIANT4['genotypes'], 'saved_variant_json': {},
        }, {'key': 18, 'variant_id': 'suffix_140593_DUP', 'family_id': 2, 'dataset_type': 'SV_WES', 'xpos': 17038717327,
            'xpos_end': 17038719636, 'ref': None, 'alt': None, 'gene_ids': ['ENSG00000275023'],
            'genotypes': GCNV_VARIANT3['genotypes'], 'saved_variant_json': {},
        }, {'key': 19, 'variant_id': 'suffix_140608_DUP', 'family_id': 2, 'dataset_type': 'SV_WES', 'xpos': 17038721781,
            'xpos_end': 17038735703, 'ref': None, 'alt': None, 'gene_ids': ['ENSG00000275023', 'ENSG00000277258', 'ENSG00000277972'],
            'genotypes': GCNV_VARIANT4['genotypes'], 'saved_variant_json': {},
        }])

        expected_tags = {
            (2,): {"Clinvar Pathogenic - Recessive": "2025-11-15", "Recessive": "2025-11-15"},
            (2, 19): {"Compound Heterozygous - One SV - Confirmed": "2025-11-15", "Compound Heterozygous - Clinvar Pathogenic/ SV": "2025-11-15"},
            (3, 4): {"Compound Heterozygous": "2025-11-15"},
            (6,): {'Mitochondrial - De Novo/ Dominant': '2025-11-15'},
            (8,): {"Mitochondrial - Pathogenic": "2025-11-15"},
            (18,): {"SV - Recessive": "2025-11-15"},
            (18, 19): {"SV - Compound Heterozygous": "2025-11-15"},
        }
        self.assertDictEqual(expected_tags, {
            tuple(sorted(tag.saved_variants.values_list('key', flat=True))): json.loads(tag.metadata)
            for tag in VariantTag.objects.filter(variant_tag_type__name='seqr Prioritized')
        })

        # Test notifications
        self.assertEqual(
            str(self.manager_user.notifications.first()),
            '1kg project nåme with uniçøde Loaded 6 new seqr prioritized variants 0 minutes ago',
        )

        mock_email.assert_called_with(
            subject='New prioritized variants tagged in seqr',
            to=['test_user_manager@test.com'],
            body='Dear seqr user,\n\nThis is to notify you that 6 new seqr prioritized variants have been tagged in seqr project 1kg project nåme with uniçøde\n\nAll the best,\nThe seqr team',
        )

        mock_slack.assert_called_with(
            'seqr-data-loading',
            '6 new seqr prioritized variants are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>\n```2: 6 new tags```',
        )

        # Test no new variants to tag
        mock_datetime.now.return_value = datetime(2025, 12, 1)
        self.reset_logs()
        mock_email.reset_mock()
        mock_slack.reset_mock()
        call_command('tag_seqr_prioritized_variants', PROJECT_GUID)
        self._assert_expected_logs(num_unchanged=7)
        mock_email.assert_not_called()
        mock_slack.assert_not_called()
        self.assertDictEqual(expected_tags, {
            tuple(sorted(tag.saved_variants.values_list('key', flat=True))): json.loads(tag.metadata)
            for tag in VariantTag.objects.filter(variant_tag_type__name='seqr Prioritized')
        })

    def _assert_expected_logs(self, num_new=0, num_unchanged=0, creation_stats=None):
        creation_stats = creation_stats or {}
        self.assert_json_logs(user=None, expected=self._dataset_type_logs(
            'SNV_INDEL', 3, SNV_INDEL_MATCHES, **creation_stats.get('SNV_INDEL', {}),
        ) + self._dataset_type_logs(
            'SV_WES', 1, SV_MATCHES, **creation_stats.get('SV', {}),
        ) + self._dataset_type_logs(
            'MITO', 1, MITO_MATCHES, **creation_stats.get('MITO', {}),
        ) + self._dataset_type_logs(
            'multi data type', 1, MULTI_TYPE_MATCHES, **creation_stats.get('MULTI', {}),
            search_dataset_types=['SNV_INDEL', 'SV_WES', 'SNV_INDEL/SV_WES'],
        ) + [
            (f'Tagged {num_new} new and 0 previously tagged variants in 1 families, found {num_unchanged} unchanged tags:', None)
        ] + [(f'  {criteria}: {count} variants', None) for criteria, (count, _) in  SNV_INDEL_MATCHES.items()] + [
            (f'  {criteria}: {count} variants', None) for criteria, (count, _) in  SV_MATCHES.items()
        ] + [(f'  {criteria}: {count} variants', None) for criteria, (count, _) in MITO_MATCHES.items()] + [
            (f'  {criteria}: {count} variants', None) for criteria, (count, _) in MULTI_TYPE_MATCHES.items()
        ])

    @classmethod
    def _dataset_type_logs(cls, dataset_type, num_families, matches, num_variants=0, tag_id_range=None, search_dataset_types=None):
        create_variants_logs = [
            (f'create {num_variants} SavedVariants', {
                'dbUpdate': {'dbEntity': 'SavedVariant', 'entityIds': mock.ANY, 'updateType': 'bulk_create'},
            }),
        ] if num_variants > 0 else []
        return  [
            (f'Searching for prioritized {dataset_type} variants in {num_families} families in project 1kg project n\u00e5me with uni\u00e7\u00f8de', None),
        ] + [(log, None) for logs in [
            cls._criteria_search_logs(search_dataset_types or [dataset_type], criteria, count, num_criteria_families, num_families)
            for criteria, (count, num_criteria_families) in matches.items()
        ] for log in logs] + create_variants_logs + [
            (f'create VariantTag VT{db_id}_seqr_prioritized', {'dbUpdate': {
                'dbEntity': 'VariantTag', 'entityId': f'VT{db_id}_seqr_prioritized', 'updateFields': ['metadata', 'variant_tag_type'], 'updateType': 'create',
            }}) for db_id in range(*(tag_id_range or [0]))
        ]

    @staticmethod
    def _criteria_search_logs(search_dataset_types, criteria, count, num_criteria_families, num_families):
        logs = [f'Searching for criteria: {criteria}']
        if num_criteria_families == 0:
            return logs
        return logs + [log for logs in [
            [f'Loading {dataset_type} data for {num_criteria_families or num_families} families',
        ] + ([f'Total results: {count}'] if i == len(search_dataset_types) - 1 else [])
        for i, dataset_type in enumerate(search_dataset_types)] for log in logs]

