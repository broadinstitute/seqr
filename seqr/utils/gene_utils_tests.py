from django.contrib.auth.models import User
from django.test import TestCase

from seqr.utils.gene_utils import get_gene, get_genes, get_genes_for_variant_display, get_genes_for_variants, \
    get_genes_with_detail
from seqr.views.utils.test_utils import GENE_FIELDS, GENE_DETAIL_FIELDS, GENE_VARIANT_FIELDS, GENE_VARIANT_DISPLAY_FIELDS

GENE_ID = 'ENSG00000223972'

class GeneUtilsTest(TestCase):
    databases = '__all__'
    fixtures = ['reference_data']

    def test_get_gene(self):
        json = get_gene(GENE_ID, user=None)
        self.assertSetEqual(set(json.keys()), GENE_DETAIL_FIELDS)

    def test_get_genes(self):
        gene_ids = {GENE_ID, 'ENSG00000227232'}
        user = User.objects.get(pk=1)

        json = get_genes(gene_ids)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_FIELDS)

        json = get_genes_for_variant_display(gene_ids)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_VARIANT_DISPLAY_FIELDS)

        json = get_genes_for_variants(gene_ids)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_VARIANT_FIELDS)

        json = get_genes_with_detail(gene_ids, user)
        self.assertSetEqual(set(json.keys()), gene_ids)
        gene = json[GENE_ID]
        self.assertSetEqual(set(gene.keys()), GENE_DETAIL_FIELDS)

        # test nested models
        self.assertSetEqual(set(gene['primateAi'].keys()), {'percentile25', 'percentile75'})
        self.assertSetEqual(
            set(gene['constraints'].keys()), {'misZ', 'misZRank', 'pli', 'pliRank', 'louef', 'louefRank', 'totalGenes'})
        self.assertSetEqual(set(gene['cnSensitivity'].keys()), {'phi', 'pts'})
        self.assertSetEqual(
            set(gene['omimPhenotypes'][0].keys()),
            {'mimNumber', 'phenotypeMimNumber', 'phenotypeDescription', 'phenotypeInheritance', 'chrom', 'start', 'end'})
        self.assertSetEqual(set(gene['genCc'].keys()), {'hgncId', 'classifications'})
        self.assertSetEqual(set(gene['clinGen'].keys()), {'haploinsufficiency', 'triplosensitivity', 'href'})

        sparse_gene = json['ENSG00000227232']
        self.assertIsNone(sparse_gene['primateAi'])
        self.assertDictEqual(sparse_gene['constraints'], {})
        self.assertDictEqual(sparse_gene['cnSensitivity'], {})
        self.assertListEqual(sparse_gene['omimPhenotypes'], [])
        self.assertDictEqual(sparse_gene['genCc'], {})
        self.assertIsNone(sparse_gene['clinGen'])
