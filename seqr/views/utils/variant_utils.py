import logging
import redis

from seqr.models import SavedVariant, VariantSearchResults
from seqr.model_utils import deprecated_retrieve_saved_variants_json
from seqr.utils.es_utils import get_es_variants_for_variant_tuples, InvalidIndexException
from settings import REDIS_SERVICE_HOSTNAME

logger = logging.getLogger(__name__)


def update_project_saved_variant_json(project, family_id=None):
    saved_variants = SavedVariant.objects.filter(family__project=project).select_related('family')
    if family_id:
        saved_variants = saved_variants.filter(family__family_id=family_id)

    saved_variants_map = {(v.xpos_start, v.ref, v.alt, v.family): v for v in saved_variants}
    variant_tuples = saved_variants_map.keys()
    saved_variants_map = {
        (xpos, ref, alt, family.guid): v for (xpos, ref, alt, family), v in saved_variants_map.items()
    }

    variants_json = _retrieve_saved_variants_json(project, variant_tuples)

    updated_saved_variant_guids = []
    for var in variants_json:
        for family_guid in var['familyGuids']:
            saved_variant = saved_variants_map.get((var['xpos'], var['ref'], var['alt'], family_guid))
            if saved_variant:
                _update_saved_variant_json(saved_variant, var)
                updated_saved_variant_guids.append(saved_variant.guid)

    return updated_saved_variant_guids


def reset_cached_search_results(project):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        keys_to_delete = []
        if project:
            result_guids = [res.guid for res in VariantSearchResults.objects.filter(families__project=project)]
            for guid in result_guids:
                keys_to_delete += redis_client.scan_iter(match='search_results__{}*'.format(guid))
        else:
            keys_to_delete = redis_client.keys(pattern='search_results__*')
        redis_client.delete(*keys_to_delete)
        logger.info('Reset {} cached results'.format(len(keys_to_delete)))
    except Exception as e:
        logger.error("Unable to reset cached search results: {}".format(e))


def _retrieve_saved_variants_json(project, variant_tuples, create_if_missing=False):
    xpos_ref_alt_tuples = []
    xpos_ref_alt_family_tuples = []
    family_id_to_guid = {}
    for xpos, ref, alt, family in variant_tuples:
        xpos_ref_alt_tuples.append((xpos, ref, alt))
        xpos_ref_alt_family_tuples.append((xpos, ref, alt, family.family_id))
        family_id_to_guid[family.family_id] = family.guid

    try:
        families = project.family_set.filter(guid__in=family_id_to_guid.values())
        return get_es_variants_for_variant_tuples(families, xpos_ref_alt_tuples)
    except InvalidIndexException:
        return deprecated_retrieve_saved_variants_json(project, xpos_ref_alt_family_tuples, create_if_missing)


def _update_saved_variant_json(saved_variant, saved_variant_json):
    saved_variant.saved_variant_json = saved_variant_json
    saved_variant.save()
