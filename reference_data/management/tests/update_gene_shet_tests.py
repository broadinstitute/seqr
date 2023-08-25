from reference_data.models import GeneShet
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneShetTest(ReferenceDataCommandTestCase):
    URL = 'https://storage.googleapis.com/seqr-reference-data/gene_constraint/shet_Zeng(2023).xlsx%20-%20All%20scores-for%20gene%20page.tsv'
    DATA = [
        'ensg	hgnc	post_mean (Shet)\n',
        'ENSG00000223972	HGNC:37225	3.01E-05\n',
        'ENSG00000227233	HGNC:26441	4.85E-05\n',
        'ENSG00000243485	HGNC:4013	5.08E-05\n',
    ]

    def test_update_gene_cn_sensitivity_command(self):
        self._test_update_command('update_gene_shet', 'GeneShet', created_records=2)

        self.assertEqual(GeneShet.objects.count(), 2)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000223972')
        self.assertEqual(record.shet, 3.01E-05)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000243485')
        self.assertEqual(record.shet, 5.08E-05)
