import logging
import redis

from seqr.models import SavedVariant, VariantSearchResults
from seqr.utils.elasticsearch.utils import get_es_variants_for_variant_ids
from seqr.utils.gene_utils import get_genes_for_variants
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from settings import REDIS_SERVICE_HOSTNAME

logger = logging.getLogger(__name__)


MAX_VARIANTS_FETCH = 1000

def update_project_saved_variant_json(project, family_id=None, user=None):
    saved_variants = SavedVariant.objects.filter(family__project=project).select_related('family')
    if family_id:
        saved_variants = saved_variants.filter(family__family_id=family_id)

    if not saved_variants:
        return []

    families = set()
    variant_ids = set()
    saved_variants_map = {}
    for v in saved_variants:
        families.add(v.family)
        variant_ids.add(v.variant_id)
        saved_variants_map[(v.variant_id, v.family.guid)] = v

    variant_ids = sorted(variant_ids)
    families = sorted(families, key=lambda f: f.guid)
    variants_json = []
    for sub_var_ids in [variant_ids[i:i+MAX_VARIANTS_FETCH] for i in range(0, len(variant_ids), MAX_VARIANTS_FETCH)]:
        variants_json += get_es_variants_for_variant_ids(families, sub_var_ids, user=user)

    updated_saved_variant_guids = []
    for var in variants_json:
        for family_guid in var['familyGuids']:
            saved_variant = saved_variants_map.get((var['variantId'], family_guid))
            if saved_variant:
                update_model_from_json(saved_variant, {'saved_variant_json': var}, user)
                updated_saved_variant_guids.append(saved_variant.guid)

    return updated_saved_variant_guids


def reset_cached_search_results(project, reset_index_metadata=False):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        keys_to_delete = []
        if project:
            result_guids = [res.guid for res in VariantSearchResults.objects.filter(families__project=project)]
            for guid in result_guids:
                keys_to_delete += redis_client.keys(pattern='search_results__{}*'.format(guid))
        else:
            keys_to_delete = redis_client.keys(pattern='search_results__*')
        if reset_index_metadata:
            keys_to_delete += redis_client.keys(pattern='index_metadata__*')
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            logger.info('Reset {} cached results'.format(len(keys_to_delete)))
        else:
            logger.info('No cached results to reset')
    except Exception as e:
        logger.error("Unable to reset cached search results: {}".format(e))


def get_variant_key(xpos=None, ref=None, alt=None, genomeVersion=None, **kwargs):
    return '{}-{}-{}_{}'.format(xpos, ref, alt, genomeVersion)


def saved_variant_genes(variants):
    gene_ids = set()
    for variant in variants:
        if isinstance(variant, list):
            for compound_het in variant:
                gene_ids.update(list(compound_het.get('transcripts', {}).keys()))
        else:
            gene_ids.update(list(variant.get('transcripts', {}).keys()))
    genes = get_genes_for_variants(gene_ids)
    for gene in genes.values():
        if gene:
            gene['locusListGuids'] = []
    return genes
