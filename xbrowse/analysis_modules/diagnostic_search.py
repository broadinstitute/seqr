from xbrowse.core.variant_filters import VariantFilter
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse.core.quality_filters import get_default_quality_filter


class DiagnosticSearchSpec():
    """
    """
    def __init__(self):
        self.analysis_module = 'diagnostic_search'
        self.project_id = None
        self.family_id = None
        self.gene_ids = None
        self.variant_filter = None

    def toJSON(self):
        d = {
            'gene_ids': self.gene_ids,
            'variant_filter': self.variant_filter.toJSON(),
            'genotype_quality_filter': self.genotype_quality_filter,
        }
        return d

    @staticmethod
    def fromJSON(spec_dict):
        spec = DiagnosticSearchSpec()
        spec.gene_ids = spec_dict.get('gene_ids')
        spec.variant_filter = VariantFilter(**spec_dict.get('variant_filter'))
        spec.genotype_quality_filter = spec_dict.get('genotype_quality_filter')
        return spec