import json

#from django.contrib.sites.models import Site
import copy

from django.conf import settings

from xbrowse import constants
from xbrowse import inheritance_modes as x_inheritance_modes
from xbrowse import quality_filters as x_quality_filters
from xbrowse.core.variant_filters import get_default_variant_filters
from xbrowse_server import mall


def default_variant_filters_json():
    filters = get_default_variant_filters(mall.get_annotator().reference_population_slugs)
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
}

DICTIONARY_INTERNAL = copy.deepcopy(DICTIONARY)
DICTIONARY_INTERNAL['annotation_reference'] = constants.ANNOTATION_REFERENCE_INTERNAL

custom_processor_result = {
    'BASE_URL':  settings.BASE_URL,
    'CONSTRUCTION_TEMPLATE':  settings.CONSTRUCTION_TEMPLATE,
    'DICTIONARY_JSON': json.dumps(DICTIONARY),
    #'CURRENT_URL':  Site.objects.get_current().domain,
}


custom_processor_result_internal = copy.deepcopy(DICTIONARY)
custom_processor_result_internal['DICTIONARY_JSON'] = json.dumps(DICTIONARY_INTERNAL)


def custom_processor(request):

    if request.user.is_staff:
        return custom_processor_result_internal
    else:
       return custom_processor_result
