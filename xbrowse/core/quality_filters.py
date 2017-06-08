import copy

DEFAULT_QUALITY_FILTERS = [

    {
        'slug': 'high_quality', 
        'name': 'High Quality', 
        'description': '', 
        'quality_filter': {
            'vcf_filter': 'pass',
            'min_gq': 20,
            'min_ab': 25,
        },
    },  

    {
        'slug': 'all_pass', 
        'name': 'All Passing Variants', 
        'description': '', 
        'quality_filter': {
            'vcf_filter': 'pass',
        },
    },  

]

DEFAULT_QUALITY_FILTERS_DICT = { item['slug']: item for item in DEFAULT_QUALITY_FILTERS }


def get_default_quality_filter(slug): 
    if slug in DEFAULT_QUALITY_FILTERS_DICT: 
        return copy.deepcopy(DEFAULT_QUALITY_FILTERS_DICT[slug]['quality_filter'])
    else: return None
