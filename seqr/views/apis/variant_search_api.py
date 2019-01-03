import json
import jmespath
from collections import defaultdict
from copy import deepcopy
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Family, Individual, SavedVariant, VariantSearch, VariantSearchResults
from seqr.utils.es_utils import get_es_variants, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.pages.project_page import get_project_details
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variant
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

    results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
    if not results_model:
        if not request.body:
            return create_json_response({}, status=400, reason='Invalid search hash: {}'.format(search_hash))

        search_context = json.loads(request.body)

        project_families = search_context.get('projectFamilies')
        if not project_families:
            return create_json_response({}, status=400, reason='Invalid search: no projects/ families specified')

        search_model = VariantSearch.objects.create(created_by=request.user, search=search_context.get('search', {}))

        results_model = VariantSearchResults.objects.create(
            search_hash=search_hash,
            variant_search=search_model,
            sort=sort
        )

        # TODO handle multiple projects
        results_model.families = Family.objects.filter(guid__in=project_families[0]['familyGuids'])
        results_model.save()

    elif results_model.sort != sort:
        results_model, _ = VariantSearchResults.objects.get_or_create(
            search_hash=search_hash,
            variant_search=results_model.variant_search,
            sort=sort
        )

    _check_results_permission(results_model, request.user)

    variants = get_es_variants(results_model, page=page, num_results=per_page)

    genes = _saved_variant_genes(variants)
    # TODO add locus lists on the client side (?)
    # TODO handle multiple projects
    _add_locus_lists(results_model.families.first().project, variants, genes)
    saved_variants_by_guid = _get_saved_variants(variants)

    return create_json_response({
        'searchedVariants': variants,
        'savedVariantsByGuid': saved_variants_by_guid,
        'genesById': genes,
        'search': _get_search_context(results_model),
    })


PREDICTION_MAP = {
    'D': 'damaging',
    'T': 'tolerated',
}

POLYPHEN_MAP = {
    'D': 'probably_damaging',
    'P': 'possibly_damaging',
    'B': 'benign',
}

MUTTASTR_MAP = {
    'A': 'disease_causing',
    'D': 'disease_causing',
    'N': 'polymorphism',
    'P': 'polymorphism',
}

VARIANT_EXPORT_DATA = [
    {'header': 'chrom'},
    {'header': 'pos'},
    {'header': 'ref'},
    {'header': 'alt'},
    {'header': 'gene', 'value_path': 'mainTranscript.geneSymbol'},
    {'header': 'worst_consequence', 'value_path': 'mainTranscript.majorConsequence'},
    {'header': '1kg_freq', 'value_path': 'populations.g1k.af'},
    {'header': 'exac_freq', 'value_path': 'populations.exac.af'},
    {'header': 'gnomad_genomes_freq', 'value_path': 'populations.gnomad_genomes.af'},
    {'header': 'gnomad_exomes_freq', 'value_path': 'populations.gnomad_exomes.af'},
    {'header': 'topmed_freq', 'value_path': 'populations.topmed.af'},
    {'header': 'sift', 'value_path': 'predictions.sift', 'process': lambda prediction: PREDICTION_MAP.get(prediction[0]) if prediction else None},
    {'header': 'polyphen', 'value_path': 'predictions.polyphen', 'process': lambda prediction: POLYPHEN_MAP.get(prediction[0]) if prediction else None},
    {'header': 'muttaster', 'value_path': 'predictions.mut_taster', 'process': lambda prediction: MUTTASTR_MAP.get(prediction[0]) if prediction else None},
    {'header': 'fathmm', 'value_path': 'predictions.fathmm', 'process': lambda prediction: PREDICTION_MAP.get(prediction[0]) if prediction else None},
    {'header': 'rsid', 'value_path': 'rsid'},
    {'header': 'hgvsc', 'value_path': 'mainTranscript.hgvsc'},
    {'header': 'hgvsp', 'value_path': 'mainTranscript.hgvsp'},
    {'header': 'clinvar_clinical_significance', 'value_path': 'clinvar.clinicalSignificance'},
    {'header': 'clinvar_gold_stars', 'value_path': 'clinvar.goldStars'},
]

VARIANT_FAMILY_EXPORT_DATA = [
    {'header': 'family_id'},
    {'header': 'tags', 'process': lambda tags: '|'.join(['{} ({})'.format(tag['name'], tag['createdBy']) for tag in tags or []])},
    {'header': 'notes', 'process': lambda notes: '|'.join(['{} ({})'.format(note['note'], note['createdBy']) for note in notes or []])},
]

VARIANT_GENOTYPE_EXPORT_DATA = [
    {'header': 'sample_id', 'value_path': 'sampleId'},
    {'header': 'num_alt_alleles', 'value_path': 'numAlt'},
    {'header': 'filter'},
    {'header': 'ad'},
    {'header': 'dp'},
    {'header': 'gq'},
    {'header': 'ab'},
]


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def export_variants_handler(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)

    _check_results_permission(results_model, request.user)

    family_ids_by_guid = {family.guid: family.family_id for family in results_model.families}

    variants = get_es_variants(results_model, page=1, num_results=results_model.total_results)

    saved_variants_by_guid = _get_saved_variants(variants)
    saved_variants_by_family = defaultdict(dict)
    for var in saved_variants_by_guid.values():
        saved_variants_by_family[var['familyGuid']]['{}-{}-{}'.format(var['xpos'], var['ref'], var['alt'])] = var

    max_families_per_variant = max([len(variant['familyGuids']) for variant in variants])
    max_samples_per_variant = max([len(variant['genotypes']) for variant in variants])

    rows = []
    for variant in variants:
        row = [_get_field_value(variant, config) for config in VARIANT_EXPORT_DATA]
        for i in range(max_families_per_variant):
            family_guid = variant['familyGuids'][i] if i < len(variant['familyGuids']) else ''
            family_tags = saved_variants_by_family[family_guid].get('{}-{}-{}'.format(variant['xpos'], variant['ref'], variant['alt'])) or {}
            family_tags['family_id'] = family_ids_by_guid.get(family_guid)
            row += [_get_field_value(family_tags, config) for config in VARIANT_FAMILY_EXPORT_DATA]
        genotypes = variant['genotypes'].values()
        for i in range(max_samples_per_variant):
            genotype = genotypes[i] if i < len(genotypes) else {}
            row += [_get_field_value(genotype, config) for config in VARIANT_GENOTYPE_EXPORT_DATA]
        rows.append(row)

    header = [config['header'] for config in VARIANT_EXPORT_DATA]
    for i in range(max_families_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_FAMILY_EXPORT_DATA]
    for i in range(max_samples_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_GENOTYPE_EXPORT_DATA]

    file_format = request.GET.get('file_format', 'tsv')

    return export_table('search_results_{}'.format(search_hash), header, rows, file_format)


def _get_field_value(value, config):
    field_value = jmespath.search(config.get('value_path', config['header']), value)
    if config.get('process'):
        field_value = config['process'](field_value)
    return field_value


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def search_context_handler(request, search_hash):
    """Search variants.
    """

    results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
    if not results_model:
        return create_json_response({}, status=400, reason='Invalid search hash: {}'.format(search_hash))

    search_context = _get_search_context(results_model)
    response = {
        'search': search_context,
    }

    for project_family in search_context.get('projectFamilies'):
        for k, v in get_project_details(project_family['projectGuid'], request.user).items():
            if response.get(k):
                response[k].update(v)
            else:
                response[k] = v

    return create_json_response(response)


def _check_results_permission(results_model, user):
    projects = {family.project for family in results_model.families.all()}
    for project in projects:
        check_permissions(project, user)


def _get_search_context(results_model):
    project_families = defaultdict(list)
    for family in results_model.families.all():
        project_families[family.project.guid].append(family.guid)

    return {
        'search': results_model.variant_search.search,
        'projectFamilies': [
            {'projectGuid': project_guid, 'familyGuids': family_guids}
            for project_guid, family_guids in project_families.items()
        ],
        'totalResults': results_model.total_results,
    }


def _get_saved_variants(variants):
    if not variants:
        return {}

    variant_q = Q()
    for variant in variants:
        variant_q |= Q(xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'], family__guid__in=variant['familyGuids'])
    saved_variants = SavedVariant.objects.filter(variant_q).prefetch_related(
        'varianttag_set', 'variantfunctionaldata_set', 'variantnote_set',
    )

    variants_by_id = {'{}-{}-{}'.format(var['xpos'], var['ref'], var['alt']): var for var in variants}
    saved_variants_by_guid = {}
    for saved_variant in saved_variants:
        variant = deepcopy(variants_by_id['{}-{}-{}'.format(saved_variant.xpos, saved_variant.ref, saved_variant.alt)])
        variant.update(get_json_for_saved_variant(saved_variant, add_tags=True))
        saved_variants_by_guid[saved_variant.guid] = variant

    return saved_variants_by_guid

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