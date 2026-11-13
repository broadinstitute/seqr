from reference_data.models import GeneConstraint
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneConstraintTest(ReferenceDataCommandTestCase):
    URL = 'https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1.2/constraint/gnomad.v4.1.2.constraint_metrics.tsv.bgz'
    DATA = [
        'gene	gene_id	transcript	canonical	mane_select	transcript_type	chromosome	mis.oe	mis.z_score	lof_hc_lc.oe_ci.upper	lof_hc_lc.pLI	lof.oe	lof.oe_ci.upper	lof.oe_ci.upper_rank	lof.pLI\n',
        'CDC7	ENSG00000097046	ENST00000234626	true	true	protein_coding	chr1	8.7387e-01	1.4024e+00	8.5721e-01	1.5553e-07	6.3549e-01	8.4606e-01	8040	1.5553e-07\n',
        'CDC7	ENSG00000097046	ENST00000426137	false	false	protein_coding	chr1	9.1640e-01	4.8704e-01	1.3749e+00	1.4221e-06	9.2930e-01	1.3780e+00	NA	1.4221e-06\n',
        'CDC7	8317	NM_003503.4	true	true	NA	NA	8.7387e-01	1.4024e+00	8.5721e-01	1.5553e-07	6.3549e-01	8.4606e-01	NA	1.5553e-07\n',
        'MTHFR	ENSG00000177000	ENST00000376590	true	true	protein_coding	chr1	8.5336e-01	1.8317e+00	9.2722e-01	1.0470e-12	7.2468e-01	9.1726e-01	9206	1.0470e-12\n',
        'MTHFR	ENSG00000177000	ENST00000413656	false	false	protein_coding	chr1	1.0886e+00	-2.2332e-01	2.2484e+00	NA	NA	NA	NA	NA\n',
        'OR4F5	ENSG00000186092	ENST00000641515	true	true	protein_coding	chr1	2.6779e-01	4.1371e+00	8.1976e-01	7.1899e-01	1.7280e-01	8.1976e-01	7626	7.1899e-01\n',
        'OR2M3	ENSG00000228198	ENST00000641626	true	true	protein_coding	chr1	1.0501e+00	-4.2203e-01	1.1320e+00	5.3605e-01	2.3441e-01	1.1120e+00	12511	5.3605e-01\n',
        'AL627309.1	ENSG00000237683	ENST00000569622	true	false	protein_coding	chr16	NA	NA	NA	NA	NA	NA	NA	NA\n',
    ]

    def test_update_gene_constraint_command(self):
        self._test_update_command('GeneConstraint', 'gnomad.v4.1.2.constraint_metrics', created_records=5)

        self.assertEqual(GeneConstraint.objects.count(), 5)
        record = GeneConstraint.objects.get(gene__gene_id = 'ENSG00000237683')
        self.assertEqual(record.mis_z, -100)
        self.assertEqual(record.mis_z_rank, 4)
        self.assertEqual(record.louef, 100)
        self.assertEqual(record.louef_rank, 4)
        self.assertEqual(record.pLI, 0)
        self.assertEqual(record.pLI_rank, 4)

        record = GeneConstraint.objects.get(gene__gene_id = 'ENSG00000097046')
        self.assertEqual(record.mis_z, 1.4024)
        self.assertEqual(record.mis_z_rank, 2)
        self.assertEqual(record.louef, 0.84606)
        self.assertEqual(record.louef_rank, 1)
        self.assertEqual(record.pLI, 1.5553e-07)
        self.assertEqual(record.pLI_rank, 2)
