from reference_data.models import GeneCopyNumberSensitivity
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneCopyNumberSensitivityTest(ReferenceDataCommandTestCase):
    URL = 'https://zenodo.org/record/6347673/files/Collins_rCNV_2022.dosage_sensitivity_scores.tsv.gz'
    DATA = [
        '#gene	pHaplo	pTriplo	\n',
        'MED13	0.994093950633184	0.999936963165105\n',
        'AL627309.1	0.999298538812066	0.998951301668586\n',
        'OR4F5	0.797834649565694	0.999754074473203\n',
    ]

    def test_update_gene_cn_sensitivity_command(self):
        self._test_update_command('GeneCopyNumberSensitivity', 'Collins_rCNV_2022', created_records=2)

        self.assertEqual(GeneCopyNumberSensitivity.objects.count(), 2)
        record = GeneCopyNumberSensitivity.objects.get(gene__gene_id='ENSG00000186092')
        self.assertEqual(record.pHI, 0.797834649565694)
        self.assertEqual(record.pTS, 0.999754074473203)
