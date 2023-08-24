from reference_data.models import GeneShet
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneShetTest(ReferenceDataCommandTestCase):
    URL = 'https://storage.googleapis.com/seqr-reference-data/Shet/Shet_Zeng_2023.tsv'
    DATA = [
        'ensg	hgnc	post_mean_shet	shet_constrained\n',
        'ENSG00000223972	HGNC:37225	3.01E-05	0\n',
        'ENSG00000227233	HGNC:26441	4.85E-05	0\n',
        'ENSG00000243485	HGNC:4013	5.08E-05	1\n',
    ]

    def test_update_gene_cn_sensitivity_command(self):
        self._test_update_command('update_gene_shet', 'GeneShet', created_records=2)

        self.assertEqual(GeneShet.objects.count(), 2)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000223972')
        self.assertEqual(record.shet, 3.01E-05)
        self.assertEqual(record.shet_constrained, False)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000243485')
        self.assertEqual(record.shet, 5.08E-05)
        self.assertEqual(record.shet_constrained, True)
