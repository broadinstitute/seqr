from reference_data.models import GeneConstraint
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateGeneConstraintTest(ReferenceDataCommandTestCase):
    URL = 'http://storage.googleapis.com/seqr-reference-data/gene_constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt'
    DATA = [
        'gene	transcript	obs_mis	exp_mis	oe_mis	mu_mis	possible_mis	obs_mis_pphen	exp_mis_pphen	oe_mis_pphen	possible_mis_pphen	obs_syn	exp_syn	oe_syn	mu_syn	possible_syn	obs_lof	mu_lof	possible_lof	exp_lof	pLI	pNull	pRec	oe_lof	oe_syn_lower	oe_syn_upper	oe_mis_lower	oe_mis_upper	oe_lof_lower	oe_lof_upper	constraint_flag	syn_z	mis_z	lof_z	oe_lof_upper_rank	oe_lof_upper_bin	oe_lof_upper_bin_6	n_sites	classic_caf	max_af	no_lofs	obs_het_lof	obs_hom_lof	defined	p	exp_hom_lof	classic_caf_afr	classic_caf_amr	classic_caf_asj	classic_caf_eas	classic_caf_fin	classic_caf_nfe	classic_caf_oth	classic_caf_sas	p_afr	p_amr	p_asj	p_eas	p_fin	p_nfe	p_oth	p_sas	transcript_type	gene_id	transcript_level	cds_length	num_coding_exons	gene_type	gene_length	exac_pLI	exac_obs_lof	exac_exp_lof	exac_oe_lof	brain_expression	chromosome	start_position	end_position\n',
        'MED13	ENST00000397786	871	1.1178e+03	7.7921e-01	5.5598e-05	14195	314	5.2975e+02	5.9273e-01	6708	422	3.8753e+02	1.0890e+00	1.9097e-05	4248	0	4.9203e-06	1257	9.8429e+01	1.0000e+00	8.9436e-40	1.8383e-16	0.0000e+00	1.0050e+00	1.1800e+00	7.3600e-01	8.2400e-01	0.0000e+00	3.0000e-02		-1.3765e+00	2.6232e+00	9.1935e+00	0	0	0	2	1.2058e-05	8.0492e-06	124782	3	0	124785	1.2021e-05	1.8031e-05	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	9.2812e-05	8.8571e-06	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	9.2760e-05	8.8276e-06	0.0000e+00	0.0000e+00	protein_coding	ENSG00000108510	2	6522	30	protein_coding	122678	1.0000e+00	0	6.4393e+01	0.0000e+00	NA	17	60019966	60142643\n',
        'AL627309.1	ENST00000423372	124	1.0192e+02	1.2167e+00	5.0212e-06	1566	20	1.1502e+01	1.7388e+00	189	43	4.3917e+01	9.7911e-01	2.1149e-06	567	5	2.7119e-07	74	6.2902e+00	9.0576e-04	4.1273e-01	5.8637e-01	7.9488e-01	7.6600e-01	1.2630e+00	1.0510e+00	1.4120e+00	4.1300e-01	1.6060e+00		1.0880e-01	-7.7730e-01	4.7671e-01	16197	8	5	0	0.0000e+00	0.0000e+00	0	0	0	0	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	protein_coding	ENSG00000237683	3	777	1	protein_coding	4479	NA	NA	NA	NA	NA	1	134901	139379\n',
        'OR4F5	ENST00000335137	67	8.2715e+01	8.1001e-01	4.1668e-06	1978	29	3.1909e+01	9.0884e-01	776	28	3.0512e+01	9.1766e-01	1.7760e-06	607	2	9.6530e-08	60	2.3369e+00	3.0354e-02	3.5740e-01	6.1225e-01	8.5584e-01	6.7900e-01	1.2580e+00	6.6400e-01	9.9300e-01	3.2500e-01	1.8400e+00		3.5753e-01	6.1403e-01	2.0421e-01	17847	9	5	0	0.0000e+00	0.0000e+00	0	0	0	0	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	0.0000e+00	protein_coding	ENSG00000186092	2	915	1	protein_coding	918	1.7633e-01	1	2.2177e+00	4.5091e-01	NA	1	69091	70008\n',
    ]

    def test_update_gene_constraint_command(self):
        self._test_update_command('GeneConstraint', 'gnomad.v2.1.1.lof_metrics.by_gene', created_records=2)

        self.assertEqual(GeneConstraint.objects.count(), 2)
        record = GeneConstraint.objects.get(gene__gene_id = 'ENSG00000237683')
        self.assertEqual(record.mis_z, -0.7773)
        self.assertEqual(record.mis_z_rank, 1)
        self.assertEqual(record.louef, 1.606)
        self.assertEqual(record.louef_rank, 0)
        self.assertEqual(record.pLI, 0.00090576)
        self.assertEqual(record.pLI_rank, 1)
