from datetime import datetime
from django.core.management import call_command
import json
import mock

from clickhouse_search.search_tests import ClickhouseSearchTestCase
from clickhouse_search.test_utils import VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT3, GCNV_VARIANT4
from seqr.models import SavedVariant, VariantTag

PROJECT_GUID = 'R0001_1kg'

SNV_INDEL_MATCHES = {
    'Clinvar Pathogenic': 0,
    'Clinvar Pathogenic -  Compound Heterozygous': 0,
    'Clinvar Both Pathogenic -  Compound Heterozygous': 0,
    'Clinvar Pathogenic - Recessive': 1,
    'Compound Heterozygous': 1,
    'Compound Heterozygous - Confirmed': 0,
    'De Novo': 0,
    'De Novo/ Dominant': 0,
    'Dominant': 0,
    'High Splice AI': 0,
    'Recessive': 1,
}
SV_MATCHES = {
    'SV - Compound Heterozygous': 1,
    'SV - De Novo/ Dominant': 0,
    'SV - Recessive': 1,
}
MULTI_TYPE_MATCHES = {
    'Compound Heterozygous - One SV': 1,
}

class CheckNewSamplesTest(ClickhouseSearchTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'panelapp', 'clickhouse_transcripts']

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    @mock.patch('seqr.utils.communication_utils._post_to_slack')
    @mock.patch('seqr.management.commands.tag_seqr_prioritized_variants.datetime')
    def test_command(self, mock_datetime, mock_slack, mock_email):
        mock_datetime.now.return_value = datetime(2025, 11, 15)

        call_command('tag_seqr_prioritized_variants', PROJECT_GUID)

        self._assert_expected_logs([
            ('create 5 SavedVariants', {
                'dbUpdate': {'dbEntity': 'SavedVariant', 'entityIds': mock.ANY, 'updateType': 'bulk_create'},
            }),
        ] + [
            (f'create VariantTag VT{db_id}_seqr_prioritized', {'dbUpdate': {
                'dbEntity': 'VariantTag', 'entityId': f'VT{db_id}_seqr_prioritized', 'updateFields': ['metadata', 'variant_tag_type'], 'updateType': 'create',
            }}) for db_id in range(1726986, 1726991)
        ] + [
            ('Tagged 5 new and 0 previously tagged variants in 1 families, found 0 unchanged tags:', None),
        ])

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
            'xpos_end': 17038719993, 'ref': None, 'alt': None, 'gene_ids': ['ENSG00000275023'],
            'genotypes': GCNV_VARIANT3['genotypes'], 'saved_variant_json': {},
        }, {'key': 19, 'variant_id': 'suffix_140608_DUP', 'family_id': 2, 'dataset_type': 'SV_WES', 'xpos': 17038721781,
            'xpos_end': 17038735703, 'ref': None, 'alt': None, 'gene_ids': ['ENSG00000275023', 'ENSG00000277258', 'ENSG00000277972'],
            'genotypes': GCNV_VARIANT4['genotypes'], 'saved_variant_json': {},
        }])

        expected_tags = {
            (2,): {"Clinvar Pathogenic - Recessive": "2025-11-15", "Recessive": "2025-11-15"},
            (2, 19): {"Compound Heterozygous - One SV": "2025-11-15"},
            (3, 4): {"Compound Heterozygous": "2025-11-15"},
            (18,): {"SV - Recessive": "2025-11-15"},
            (18, 19): {"SV - Compound Heterozygous": "2025-11-15"},
        }
        self.assertDictEqual(expected_tags, {
            tuple(tag.saved_variants.values_list('key', flat=True)): json.loads(tag.metadata)
            for tag in VariantTag.objects.filter(variant_tag_type__name='seqr Prioritized')
        })

        # Test notifications
        self.assertEqual(
            str(self.manager_user.notifications.first()),
            '1kg project nåme with uniçøde Loaded 5 new seqr prioritized variants 0 minutes ago',
        )

        mock_email.assert_called_with(
            subject='New prioritized variants tagged in seqr',
            to=['test_user_manager@test.com'],
            body='Dear seqr user,\n\nThis is to notify you that 5 new seqr prioritized variants have been tagged in seqr project 1kg project nåme with uniçøde\n\nAll the best,\nThe seqr team',
        )

        mock_slack.assert_called_with(
            'seqr-data-loading',
            '5 new seqr prioritized variants are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>\n```2: 5 new tags```',
        )

        # Test no new variants to tag
        mock_datetime.now.return_value = datetime(2025, 12, 1)
        self.reset_logs()
        mock_email.reset_mock()
        mock_slack.reset_mock()
        call_command('tag_seqr_prioritized_variants', PROJECT_GUID)
        self._assert_expected_logs([
            ('Tagged 0 new and 0 previously tagged variants in 1 families, found 5 unchanged tags:', None),
        ])
        mock_email.assert_not_called()
        mock_slack.assert_not_called()
        self.assertDictEqual(expected_tags, {
            tuple(tag.saved_variants.values_list('key', flat=True)): json.loads(tag.metadata)
            for tag in VariantTag.objects.filter(variant_tag_type__name='seqr Prioritized')
        })

    def _assert_expected_logs(self, model_creation_logs):
        self.assert_json_logs(user=None, expected=[
            ('Searching for prioritized SNV_INDEL variants in 3 families in project 1kg project n\u00e5me with uni\u00e7\u00f8de', None),
        ] + [(f'Found {count} variants for criteria: {criteria}', None) for criteria, count in SNV_INDEL_MATCHES.items()] + [
            ('Searching for prioritized SV_WES variants in 1 families in project 1kg project n\u00e5me with uni\u00e7\u00f8de', None),
        ] + [(f'Found {count} variants for criteria: {criteria}', None) for criteria, count in SV_MATCHES.items()] + [
            ('Searching for prioritized multi data type variants in 1 families in project 1kg project n\u00e5me with uni\u00e7\u00f8de', None),
        ] + [(f'Found {count} variants for criteria: {criteria}', None) for criteria, count in MULTI_TYPE_MATCHES.items()] +
        model_creation_logs + [(f'  {criteria}: {count} variants', None) for criteria, count in  SNV_INDEL_MATCHES.items()] + [
            (f'  {criteria}: {count} variants', None) for criteria, count in  SV_MATCHES.items()
        ] + [(f'  {criteria}: {count} variants', None) for criteria, count in  MULTI_TYPE_MATCHES.items()])

