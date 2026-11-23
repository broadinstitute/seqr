from reference_data.models import GeneConstraint
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneConstraintTest(ReferenceDataCommandTestCase):
    URL = 'https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1.2/constraint/gnomad.v4.1.2.constraint_metrics.tsv.bgz'
    DATA = [
        'gene	gene_id	transcript	canonical	mane_select	transcript_type	chromosome	constraint_flags	mis.oe	mis.z_score	lof_hc_lc.oe_ci.upper	lof_hc_lc.pLI	lof.oe	lof.oe_ci.upper	lof.oe_ci.upper_rank	lof.pLI\n',
        'DDX11L1	ENSG00000223972	ENST00000456328	true	false	protein_coding	chr1	[]	8.7387e-01	1.4024e+00	8.5721e-01	1.5553e-07	6.3549e-01	8.4606e-01	8040	1.5553e-07\n',
        'WASH7P	ENSG00000227232	ENST00000624735	true	true	protein_coding	chr1	["no_exp_lof"]	1.0501e+00	-4.2203e-01	NA	NA	NA	NA	NA	NA\n',
        'RP11	ENSG00000135953	ENST00000258436	false	false	protein_coding	chr1	[]	9.1640e-01	1.4024e+00	1.3749e+00	1.4221e-06	9.2930e-01	1.3780e+00	NA	1.4221e-06\n',
        'CDC7	8317	NM_003503.4	true	true	NA	NA	[]	8.7387e-01	1.4024e+00	8.5721e-01	1.5553e-07	6.3549e-01	8.4606e-01	NA	1.5553e-07\n',
        'MTHFR	ENSG00000177000	ENST00000376590	true	true	protein_coding	chr1	[]	8.5336e-01	1.8317e+00	9.2722e-01	1.0470e-12	7.2468e-01	9.1726e-01	9206	1.0470e-12\n',
    ]

    def test_update_gene_constraint_command(self):
        self._test_update_command(
            'GeneConstraint', '4.1.2', existing_records=3, created_records=3, skipped_records=0,
            additional_logs=[(7, 'Skipped 2 records with unrecognized or duplicated transcripts', None)],
        )

        self.assertEqual(GeneConstraint.objects.count(), 3)
        self.assertEqual(GeneConstraint.objects.filter(canonical=True).count(), 2)
        record = GeneConstraint.objects.get(transcript__transcript_id='ENST00000456328')
        self.assertEqual(record.transcript.gene.gene_id, 'ENSG00000223972')
        self.assertTrue(record.canonical)
        self.assertFalse(record.mane_select)
        self.assertListEqual(record.constraint_flags, [])
        self.assertEqual(record.mis_z, 1.4024)
        self.assertEqual(record.mis_z_rank, 0)
        self.assertEqual(record.louef, 0.84606)
        self.assertEqual(record.louef_rank, 0)
        self.assertEqual(record.pLI, 1.5553e-07)
        self.assertEqual(record.pLI_rank, 0)

        record = GeneConstraint.objects.get(transcript__transcript_id='ENST00000624735')
        self.assertTrue(record.canonical)
        self.assertTrue(record.mane_select)
        self.assertListEqual(record.constraint_flags, ['no_exp_lof'])
        self.assertEqual(record.mis_z, -0.42203)
        self.assertEqual(record.mis_z_rank, 1)
        self.assertIsNone(record.louef)
        self.assertEqual(record.louef_rank, 1)
        self.assertIsNone(record.pLI)
        self.assertEqual(record.pLI_rank, 1)

        record = GeneConstraint.objects.get(transcript__transcript_id='ENST00000258436')
        self.assertFalse(record.canonical)
        self.assertFalse(record.mane_select)
        self.assertListEqual(record.constraint_flags, [])
        self.assertEqual(record.mis_z, 1.4024)
        self.assertEqual(record.mis_z_rank, 0)
        self.assertEqual(record.louef, 1.378)
        self.assertEqual(record.louef_rank, 1)
        self.assertEqual(record.pLI, 1.4221e-06)
        self.assertEqual(record.pLI_rank, 0)
