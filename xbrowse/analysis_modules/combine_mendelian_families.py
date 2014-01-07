from xbrowse.core.variant_filters import VariantFilter


class CombineMendelianFamiliesSpec():
    """
    """
    def __init__(self):
        self.analysis_module = 'combine_mendelian_families'
        self.project_id = None
        self.family_group_id = None
        self.inheritance_mode = None
        self.variant_filter = None
        self.genotype_quality_filter = None

    def toJSON(self):
        d = {
            'inheritance_mode': self.inheritance_mode,
            'variant_filter': self.variant_filter.toJSON(),
            'genotype_quality_filter': self.genotype_quality_filter,
        }
        return d

    @staticmethod
    def fromJSON(spec_dict):
        spec = CombineMendelianFamiliesSpec()
        spec.inheritance_mode = spec_dict.get('inheritance_mode')
        spec.variant_filter = VariantFilter(**spec_dict.get('variant_filter'))
        spec.genotype_quality_filter = spec_dict.get('genotype_quality_filter')
        return spec

