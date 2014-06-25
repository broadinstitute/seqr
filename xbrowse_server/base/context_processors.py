from django.contrib.sites.models import Site
from django.conf import settings
from xbrowse import constants
from xbrowse import inheritance_modes as x_inheritance_modes
from xbrowse import inheritance as x_inheritance
from xbrowse import variant_filters as x_variant_filters
from xbrowse import quality_filters as x_quality_filters

import json
import copy
from xbrowse.core.variant_filters import get_default_variant_filters


def default_variant_filters_json():
    filters = get_default_variant_filters(settings.ANNOTATOR.reference_population_slugs)
    for item in filters:
        item['variant_filter'] = item['variant_filter'].toJSON()
    return filters


DICTIONARY = {
    'tissue_types': constants.TISSUE_TYPES,
    'standard_inheritances': x_inheritance_modes.INHERITANCE_DEFAULTS,
    'genotype_options': constants.GENOTYPE_OPTIONS,
    'burden_filter_options': constants.BURDEN_FILTER_OPTIONS,
    'default_variant_filters': default_variant_filters_json(),
    'default_quality_filters': x_quality_filters.DEFAULT_QUALITY_FILTERS,
    'annotation_reference': constants.ANNOTATION_REFERENCE,
    'expression_reference': constants.EXPRESSION_REFERENCE,
    'gene_reference': constants.GENE_REFERENCE,

    'analysis_status_options': {
        'S': 'Solved',
        'I': 'In progress',
        'Q': 'Waiting for data'
    }

}


def custom_processor(request): 

    return {
        'BASE_URL':  settings.BASE_URL,
        'URL_PREFIX':  settings.URL_PREFIX,
        'CURRENT_URL':  Site.objects.get_current().domain,
        'DICTIONARY_JSON': json.dumps(DICTIONARY),
    }