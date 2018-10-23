import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Family, Individual, SavedVariant, VariantSearch
from seqr.utils.es_utils import get_es_variants, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    get_json_for_variant_tag, get_json_for_variant_functional_data, get_json_for_variant_note
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.model_utils import find_matching_xbrowse_model

from xbrowse_server.mall import get_datastore

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
    project = get_project_and_check_permissions(search.get('projectGuid'), request.user)
    family = Family.objects.get(guid=search.get('familyGuid'))
    individuals = family.individual_set.all()

    if search_model.results:
        variants = json.loads(search_model.results)
    else:
        variants, total_results, es_index = get_es_variants(search, individuals, sort=sort)
        search_model.results = json.dumps(variants)
        search_model.total_results = total_results
        search_model.es_index = es_index
        search_model.save()

    genes = _saved_variant_genes(variants)
    # TODO add locus lists on the client side (?)
    _add_locus_lists(project, variants, genes)
    searched_variants, saved_variants_by_guid = _get_saved_variants(variants, project, family)

    return create_json_response({
        'searchedVariants': searched_variants,
        'savedVariantsByGuid': saved_variants_by_guid,
        'genesById': genes,
        'search': search,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def variant_transcripts(request):
    project = get_project_and_check_permissions(request.GET.get('projectGuid'), request.user)
    family = Family.objects.get(guid=request.GET.get('familyGuid'))

    base_project = find_matching_xbrowse_model(project)
    # TODO use new es utils
    loaded_variant = get_datastore(base_project).get_single_variant(
        base_project.project_id,
        family.family_id,
        int(request.GET.get('xpos')),
        request.GET.get('ref'),
        request.GET.get('alt'),
    )

    transcripts = _parsed_variant_transcripts(loaded_variant.annotation)
    return create_json_response({
        'transcripts': transcripts,
        'genesById': get_genes(transcripts.keys()),
    })



def _parsed_variant_transcripts(annotation):
    transcripts = defaultdict(list)
    for i, vep_a in enumerate(annotation['vep_annotation']):
        transcripts[vep_a.get('gene', vep_a.get('gene_id'))].append({
            'transcriptId': vep_a.get('feature') or vep_a.get('transcript_id'),
            'isChosenTranscript': i == annotation.get('worst_vep_annotation_index'),
            'aminoAcids': vep_a.get('amino_acids'),
            'canonical': vep_a.get('canonical'),
            'cdnaPosition': vep_a.get('cdna_position') or vep_a.get('cdna_start'),
            'cdsPosition': vep_a.get('cds_position'),
            'codons': vep_a.get('codons'),
            'consequence': vep_a.get('consequence') or vep_a.get('major_consequence'),
            'hgvsc': vep_a.get('hgvsc'),
            'hgvsp': vep_a.get('hgvsp'),
        })
    return transcripts


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
            variant.update({
                'variantGuid': saved_variant.guid if saved_variant else None,
                'tags': [
                    get_json_for_variant_tag(tag) for tag in saved_variant.varianttag_set.all()
                ] if saved_variant else [],
                'functionalData': [
                    get_json_for_variant_functional_data(tag) for tag in saved_variant.variantfunctionaldata_set.all()
                ] if saved_variant else [],
                'notes': [
                    get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()
                ] if saved_variant else [],
            })
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