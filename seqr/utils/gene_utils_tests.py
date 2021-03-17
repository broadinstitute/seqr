from django.contrib.auth.models import User
from django.test import TestCase

from seqr.utils.gene_utils import get_gene, get_genes
from seqr.views.utils.test_utils import GENE_FIELDS, GENE_DETAIL_FIELDS, GENE_VARIANT_FIELDS

GENE_ID = 'ENSG00000223972'

class GeneUtilsTest(TestCase):
    databases = '__all__'
    fixtures = ['reference_data']

    def test_get_gene(self):
        json = get_gene(GENE_ID, user=None)
        self.assertSetEqual(set(json.keys()), GENE_DETAIL_FIELDS)

    def test_get_genes(self):
        gene_ids = {GENE_ID, 'ENSG00000227232'}
        user = User.objects.filter().first()

        json = get_genes(gene_ids, user=user)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_FIELDS)

        fields = {'constraints', 'omimPhenotypes', 'mimNumber', 'cnSensitivity'}
        fields.update(GENE_FIELDS)
        json = get_genes(gene_ids, user=user, add_variant_gene_display_fields=True)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), fields)

        json = get_genes(gene_ids, user=user, add_variant_gene_fields=True)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_VARIANT_FIELDS)

        json = get_genes(gene_ids, user=user, add_all=True)
        self.assertSetEqual(set(json.keys()), gene_ids)
        self.assertSetEqual(set(json[GENE_ID].keys()), GENE_DETAIL_FIELDS)


