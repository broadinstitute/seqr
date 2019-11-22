from xbrowse.core.variant_filters import VariantFilter


class CohortGeneSearchSpec():
    """
    """
    def __init__(self):
        self.analysis_module = 'cohort_gene_search'
        self.project_id = None
        self.cohort_id = None
        self.inheritance_mode = None
        self.variant_filter = None
        self.quality_filter = None

    def toJSON(self):
        d = {
            'inheritance_mode': self.inheritance_mode,
            'variant_filter': self.variant_filter.toJSON(),
            'quality_filter': self.quality_filter,
        }
        return d

    @staticmethod
    def fromJSON(spec_dict):
        spec = CohortGeneSearchSpec()
        spec.inheritance_mode = spec_dict.get('inheritance_mode')
        spec.variant_filter = VariantFilter(**spec_dict.get('variant_filter'))
        spec.quality_filter = spec_dict.get('quality_filter')
        return spec

