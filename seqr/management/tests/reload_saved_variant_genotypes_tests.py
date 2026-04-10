from django.core.management import call_command

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase
from seqr.models import SavedVariant, Dataset


class ReloadSavedVariantGenotypesTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'report_variants', 'clickhouse_saved_variants']

    def test_command(self):
        # Update fixture data
        for dataset in Dataset.objects.filter(id__in=[143, 149]):
            dataset.active_individuals.set([18])

        call_command('reload_saved_variant_genotypes', 'R0004_non_analyst_project')
        self.assert_json_logs(user=None, expected=[
            ('Reloading genotypes for 0 MITO variants in family F000014_14', None),
            ('Reloading genotypes for 1 SNV_INDEL variants in family F000014_14', None),
            ('update 1 SavedVariants', {'dbUpdate': {
                'dbEntity': 'SavedVariant',
                'entityIds': ['SV0000006_1248367227_r0004_non'],
                'updateFields': ['genotypes'],
                'updateType': 'bulk_update',
            }}),
            ('Reloading genotypes for 0 SV_WGS variants in family F000014_14', None),
            ('Done', None),
        ])
        saved_variant = SavedVariant.objects.get(guid='SV0000006_1248367227_r0004_non')
        self.assertDictEqual(saved_variant.genotypes, {'I000018_na21234': {
            'ab': 0.0, 'dp': 49, 'gq': 99, 'numAlt': 2, 'filters': [],
            'sampleId': 'NA21234', 'familyGuid': 'F000014_14', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234',
        }})
        unchanged_saved_variant = SavedVariant.objects.get(guid='SV0000009_25000014783_r0004_no')
        self.assertDictEqual(unchanged_saved_variant.genotypes, {'I000018_na21234': {
            'sampleId': 'NA20885', 'numAlt': 2, 'dp': 3943, 'hl': 1.0, 'mitoCn': 214, 'contamination': 0.0, 'filters': ['artifact_prone_site'],
        }})

        self.reset_logs()
        call_command('reload_saved_variant_genotypes', 'R0001_1kg', '--family-guid=F000002_2')
        self.assert_json_logs(user=None, expected=[
            ('Reloading genotypes for 1 SNV_INDEL variants in family F000002_2', None),
            ('update 1 SavedVariants', {'dbUpdate': {
                'dbEntity': 'SavedVariant',
                'entityIds': ['SV0000002_1248367227_r0390_100'],
                'updateFields': ['genotypes'],
                'updateType': 'bulk_update',
            }}),
            ('Done', None),
        ])
