from django.conf import settings
from xbrowse_server.mall import get_reference, get_mall, get_cnv_store, get_coverage_store


class GeneDiagnosticInfo():

    def __init__(self, gene_id):
        self._gene_id = gene_id
        self._gene_phenotype_summary = None
        self._gene_sequencing_summary = None
        self._variants = None
        self._cnvs = None

    def toJSON(self):
        return {
            'gene_id': self._gene_id,
            'variants': [v.toJSON() for v in self._variants],
            'cnvs': self._cnvs,
            'gene_phenotype_summary': self._gene_phenotype_summary,
            'gene_sequencing_summary': self._gene_sequencing_summary,
        }


def get_gene_phenotype_summary(reference, gene_id):
    gene = reference.get_gene(gene_id)
    return {
        'gene_id': gene_id,
        'symbol': gene['symbol'],
        'coding_size': 1000,  # TODO
    }


def get_gene_sequencing_summary(coverage_store, family, gene_id):
    individuals = family.get_individuals_with_variant_data()
    by_sample = {indiv.indiv_id: {} for indiv in individuals}
    for indiv in individuals:
        by_sample[indiv.indiv_id] = coverage_store.get_coverage_for_gene(indiv.get_coverage_store_id(), gene_id)['gene_totals']
    return {
        'coverage_by_sample': by_sample,
    }


def get_diagnostic_search_variants_in_family(datastore, family, gene_id, variant_filter=None):
    """
    Get any variants with an alternate allele in at least one unaffected indiv
    """
    affected_indiv_ids = [i.indiv_id for i in family.get_individuals_with_variant_data() if i.affected == 'A']
    variants = []
    for variant in datastore.get_variants_in_gene(family.project.project_id, family.family_id, gene_id, variant_filter=variant_filter):
        for indiv_id in affected_indiv_ids:
            geno = variant.get_genotype(indiv_id)
            if geno and geno.num_alt and geno.num_alt > 0:
                variants.append(variant)
                break
    return variants


def get_diagnostic_search_cnvs_in_family(cnv_store, family, gene_id):
    """
    Get any variants with an alternate allele in at least one unaffected indiv
    """
    cnvs = []
    for indiv in family.get_individuals():
        indiv_cnvs = cnv_store.get_cnvs_for_gene(str(indiv.pk), gene_id)
        for c in indiv_cnvs:
            c['indiv_id'] = indiv.indiv_id
        cnvs.extend(indiv_cnvs)
    return cnvs


def get_gene_diangostic_info(family, gene_id, variant_filter=None):

    diagnostic_info = GeneDiagnosticInfo(gene_id)

    diagnostic_info._gene_phenotype_summary = get_gene_phenotype_summary(get_reference(), gene_id)
    diagnostic_info._gene_sequencing_summary = get_gene_sequencing_summary(get_coverage_store(), family, gene_id)
    diagnostic_info._variants = get_diagnostic_search_variants_in_family(
        get_mall(family.project).variant_store,
        family,
        gene_id,
        variant_filter
    )
    diagnostic_info._cnvs = get_diagnostic_search_cnvs_in_family(
        get_cnv_store(),
        family,
        gene_id,
    )

    return diagnostic_info