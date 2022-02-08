import logging
import redis

from seqr.models import SavedVariant, VariantSearchResults, Family
from seqr.utils.elasticsearch.utils import get_es_variants_for_variant_ids
from seqr.utils.gene_utils import get_genes_for_variants
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.permissions_utils import has_case_review_permissions
from seqr.views.utils.project_context_utils import add_project_tag_types, add_families_context
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

LOAD_PROJECT_TAG_TYPES_CONTEXT_PARAM = 'loadProjectTagTypes'
LOAD_FAMILY_CONTEXT_PARAM = 'loadFamilyContext'

def get_variant_request_project_context(request, response, project_guids, variants, is_analyst, add_all_context=False, include_igv=True):
    if add_all_context or request.GET.get(LOAD_PROJECT_TAG_TYPES_CONTEXT_PARAM) == 'true':
        response['projectsByGuid'] = {project_guid: {'projectGuid': project_guid} for project_guid in project_guids}
        add_project_tag_types(response['projectsByGuid'])

    if add_all_context or request.GET.get(LOAD_FAMILY_CONTEXT_PARAM) == 'true':
        loaded_family_guids = set()
        for variant in variants:
            loaded_family_guids.update(variant['familyGuids'])
        families = Family.objects.filter(guid__in=loaded_family_guids).prefetch_related('project')
        projects = {family.project for family in families}
        project = list(projects)[0] if len(projects) == 1 else None

        add_families_context(
            response, families, project_guid=project.guid if project else None, user=request.user, is_analyst=is_analyst,
            has_case_review_perm=bool(project) and has_case_review_permissions(project, request.user), include_igv=include_igv,
        )

