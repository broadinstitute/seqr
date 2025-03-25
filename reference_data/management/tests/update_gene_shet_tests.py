from reference_data.models import GeneShet
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneShetTest(ReferenceDataCommandTestCase):
    URL = 'https://zenodo.org/record/7939768/files/s_het_estimates.genebayes.tsv'
    DATA = [
        'ensg	hgnc	chrom	obs_lof	exp_lof	prior_mean	post_mean	post_lower_95	post_upper_95\n',
        'ENSG00000223972	HGNC:37225	chr15	26.0	21.66	0.00059216	3.01e-05	1.05e-06	0.00010405\n',
        'ENSG00000227233	HGNC:26441	chr5	31.0	28.55	0.00038727	4.853e-05	3.05e-06	0.00015705\n',
        'ENSG00000243485	HGNC:4013	chr19	17.0	11.327	0.00082297	5.083e-05	3.05e-06	0.00016605\n'
    ]

    def test_update_gene_cn_sensitivity_command(self):
        self._test_update_command('GeneShet', '7939768', created_records=2)

        self.assertEqual(GeneShet.objects.count(), 2)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000223972')
        self.assertEqual(record.post_mean, 3.01E-05)
        record = GeneShet.objects.get(gene__gene_id='ENSG00000243485')
        self.assertEqual(record.post_mean, 5.083E-05)
