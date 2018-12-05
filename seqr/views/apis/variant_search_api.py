import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Family, Individual, SavedVariant, VariantSearch
from seqr.utils.es_utils import get_es_variants, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import add_additional_json_fields_for_saved_variant
from seqr.views.utils.permissions_utils import check_permissions


GENOTYPE_AC_LOOKUP = {
    'ref_ref': [0, 0],
    'has_ref': [0, 1],
    'ref_alt': [1, 1],
    'has_alt': [1, 2],
    'alt_alt': [2, 2],
}
AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants_handler(request, search_hash):
    """Search variants.
    """
    page = int(request.GET.get('page') or 1)
    per_page = int(request.GET.get('per_page') or 100)
    sort = request.GET.get('sort') or XPOS_SORT_KEY
    if sort == PATHOGENICTY_SORT_KEY and request.user.is_staff:
        sort = PATHOGENICTY_HGMD_SORT_KEY

    search_models = VariantSearch.objects.filter(search_hash=search_hash)
    if not search_models:
        search_json = request.body
        if not search_json:
            return create_json_response({}, status=400, reason='Invalid search hash: {}'.format(search_hash))
    else:
        search_json = search_models[0].search
    search = json.loads(search_json)
    search_model = search_models.filter(sort=sort).first()
    if not search_model:
        search_model = VariantSearch.objects.create(search_hash=search_hash, sort=sort, search=search_json)

    # TODO this is only mendelian variant search, should be others and not require project/ family
    family = Family.objects.get(guid=search.get('familyGuid'))
    project = family.project
    check_permissions(project, request.user)
    individuals = family.individual_set.all()

    search_results = json.loads(search_model.results or '[]')
    offset = (page - 1) * per_page
    if len(search_results) >= page * per_page or (search_model.total_results and len(search_results) == search_model.total_results):
        variants = search_results[offset:(page * per_page)]
    else:
        variants, total_results, es_index = get_es_variants(search, individuals, sort=sort, offset=offset, num_results=per_page)
        # Only save contiguous pages of results
        if len(search_results) == (page - 1) * per_page:
            search_model.results = json.dumps(search_results + variants)
        search_model.total_results = total_results
        search_model.es_index = es_index
        search_model.save()
        # Compound het searches return all variants not just the requested page
        if len(variants) > per_page:
            variants = variants[:per_page]

    genes = _saved_variant_genes(variants)
    # TODO add locus lists on the client side (?)
    _add_locus_lists(project, variants, genes)
    searched_variants, saved_variants_by_guid = _get_saved_variants(variants, project, family)
    search['totalResults'] = search_model.total_results

    return create_json_response({
        'searchedVariants': searched_variants,
        'savedVariantsByGuid': saved_variants_by_guid,
        'genesById': genes,
        'search': search,
    })


def _get_saved_variants(variants, project, family):
    variant_q = Q()
    for variant in variants:
        variant_q |= Q(xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'])
    saved_variants = SavedVariant.objects.filter(project=project, family=family).filter(variant_q).prefetch_related(
        'varianttag_set', 'variantfunctionaldata_set', 'variantnote_set',
    )

    # TODO may not be unique in non-family speific searches
    saved_variants_by_id = {'{}-{}-{}'.format(var.xpos, var.ref, var.alt): var for var in saved_variants}
    saved_variants_by_guid = {}
    searched_variants = []
    for variant in variants:
        variant_key = '{}-{}-{}'.format(variant['xpos'], variant['ref'], variant['alt'])
        if saved_variants_by_id.get(variant_key):
            saved_variant = saved_variants_by_id[variant_key]
            add_additional_json_fields_for_saved_variant(variant, saved_variant, add_tags=True)
            saved_variants_by_guid[saved_variant.guid] = variant
            searched_variants.append({'variantGuid': saved_variant.guid})
        else:
            variant.update({
                'variantGuid':  None,
                'tags': [],
                'functionalData': [],
                'notes': [],
            })
            searched_variants.append(variant)

    return searched_variants, saved_variants_by_guid

# Search spec conversion
# variant_filter = {}
# if search.get('freqs'):
#     freqs = search.get('freqs')
#     variant_filter['ref_freqs'] = [[k, v['af']] for k, v in freqs.items() if v.get('af') is not None]
#     variant_filter['ref_acs'] = [[k, v['ac']] for k, v in freqs.items() if v.get('ac') is not None and not v.get('af')]
#     variant_filter['ref_hom_hemi'] = [[k, v['hh']] for k, v in freqs.items() if v.get('hh') is not None]
# if search.get('annotations'):
#     variant_filter['so_annotations'] = [ann for annotations in search.get('annotations').values() for ann in annotations]
# if search.get('locus'):
#     locus_json = search.get('locus')
#     genes, intervals, invalid_items = parse_locus_list_items(locus_json, all_new=True)
#     if invalid_items:
#         error = 'Invalid genes/intervals: {}'.format(', '.join(invalid_items))
#         return create_json_response({'error': error}, status=400, reason=error)
#     variant_filter['genes'] = genes.keys()
#     variant_filter['locations'] = [(get_xpos(i['chrom'], i['start']), get_xpos(i['chrom'], i['end'])) for i in intervals]
#     variant_filter['exclude_genes'] = locus_json.get('excludeLocations', False)
#
# inheritance = search.get('inheritance', {})
# inheritance_mode = inheritance.get('mode')
# search_mode = 'all_variants'
# genotype_inheritance_filter = {}
# allele_count_filter = {}
# if inheritance.get('filter') and inheritance['filter'].get(AFFECTED) and inheritance['filter'].get(UNAFFECTED):
#     inheritance_mode = 'custom'
#     if inheritance['filter'][AFFECTED].get('genotype') and inheritance['filter'][UNAFFECTED].get('genotype'):
#         search_mode = 'allele_count'
#         allele_count_filter = {
#             'affected_gte': GENOTYPE_AC_LOOKUP[inheritance['filter'][AFFECTED]['genotype']][0],
#             'affected_lte': GENOTYPE_AC_LOOKUP[inheritance['filter'][AFFECTED]['genotype']][1],
#             'unaffected_gte': GENOTYPE_AC_LOOKUP[inheritance['filter'][UNAFFECTED]['genotype']][0],
#             'unaffected_lte': GENOTYPE_AC_LOOKUP[inheritance['filter'][UNAFFECTED]['genotype']][1],
#         }
#     else:
#         search_mode = 'custom_inheritance'
#         for affected_status, filters in inheritance['filter'].items():
#             if filters.get('individuals'):
#                 genotype_inheritance_filter.update(filters['individuals'])
#             else:
#                 for individual in Individual.objects.filter(family=family, affected=affected_status).only('individual_id'):
#                     genotype_inheritance_filter[individual.individual_id] = filters['genotype']
# elif inheritance_mode:
#     search_mode = 'standard_inheritance'
#
# search_spec = MendelianVariantSearchSpec.fromJSON({
#     'family_id': family.family_id,
#     'search_mode': search_mode,
#     'inheritance_mode': inheritance_mode,
#     'genotype_inheritance_filter': genotype_inheritance_filter,
#     'allele_count_filter': allele_count_filter,
#     'variant_filter': variant_filter,
#     'quality_filter': search.get('qualityFilter', {}),
# })