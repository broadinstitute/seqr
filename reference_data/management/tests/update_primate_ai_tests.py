from reference_data.models import PrimateAI
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase


class UpdatePrimateAiTest(ReferenceDataCommandTestCase):
    URL = 'http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.cleaned_v0.2.txt'
    DATA = [
        'ucscid	genesymbol	nAllSNPs	pcnt75	pcnt25	nClinvarBenignSNPs	benign_mean	benign_std	nClinvarPathogenicSNPs	pathogenic_mean	pathogenic_std\n',
        'uc021qil.1	CREB3L1	3744	0.748042136	0.432699919	NA	NA	NA	NA	NA	NA\n',
        'uc010nxu.2	OR4F29	2038	0.593389094	0.383666202	NA	NA	NA	NA	NA	NA\n',
        'uc001aal.1	OR4F5	2019	0.569617867	0.335699245	NA	NA	NA	NA	NA	NA\n',
        'uc002ehz.4	MMP2	4389	0.78644371	0.556205034	NA	NA	NA	2	0.842780441	0.114728231\n',
    ]

    def test_update_primate_ai_command(self):
        self._test_update_command('PrimateAI', 'cleaned_v0.2', created_records=2, skipped_records=2)

        self.assertEqual(PrimateAI.objects.all().count(), 2)
        record = PrimateAI.objects.get(gene__gene_id = 'ENSG00000235249')
        self.assertEqual(record.percentile_25, 0.383666202)
        self.assertEqual(record.percentile_75, 0.593389094)
