from xbrowse.core.variant_filters import AlleleCountFilter, VariantFilter


class MendelianVariantSearchSpec():
    """
    This class contains all the information from one execution of Mendelian Variant Search
    Note that it might not capture all the context of the search -
    eg. if you typed a gene symbol, this will contain the gene ID
    But a spec should always be enough to
    """
    def __init__(self):
        self.analysis_module = 'mendelian_variant_search'  # TODO: is this needed? if so class property
        self.project_id = None  # todo: is this needed?
        self.family_id = None  # todo: is this needed?
        self.search_mode = None
        self.inheritance_mode = None
        self.genotype_inheritance_filter = None
        self.gene_burden_filter = None
        self.allele_count_filter = None
        self.variant_filter = None
        self.quality_filter = None

    def toJSON(self):
        d = {
            'search_mode': self.search_mode,
            'inheritance_mode': self.inheritance_mode,
            'genotype_inheritance_filter': self.genotype_inheritance_filter,
            'gene_burden_filter': self.gene_burden_filter,
            'variant_filter': self.variant_filter.toJSON(),
            'quality_filter': self.quality_filter,
        }

        if self.allele_count_filter:
            d['allele_count_filter'] = self.allele_count_filter._asdict()
        return d

    @staticmethod
    def fromJSON(spec_dict):
        spec = MendelianVariantSearchSpec()
        spec.search_mode = spec_dict.get('search_mode')
        spec.inheritance_mode = spec_dict.get('inheritance_mode')
        spec.genotype_inheritance_filter = spec_dict.get('genotype_inheritance_filter')
        spec.gene_burden_filter = spec_dict.get('gene_burden_filter')
        spec.variant_filter = VariantFilter(**spec_dict.get('variant_filter'))
        spec.quality_filter = spec_dict.get('quality_filter')
        if 'allele_count_filter' in spec_dict:
            spec.allele_count_filter = AlleleCountFilter(**spec_dict.get('allele_count_filter'))
        return spec

