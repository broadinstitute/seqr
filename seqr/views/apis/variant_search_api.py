from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Family, SavedVariant
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _variant_details, _saved_variant_genes, _add_locus_lists
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    get_json_for_variant_tag, get_json_for_variant_functional_data, get_json_for_variant_note
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.model_utils import find_matching_xbrowse_model



from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.api import utils as api_utils
from xbrowse_server.mall import get_reference
from xbrowse_server.search_cache import utils as cache_utils
from xbrowse import Variant
from xbrowse.analysis_modules.mendelian_variant_search import MendelianVariantSearchSpec


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants_handler(request):
    """Search variants.
    """

    # TODO this is only mendelian variant search, should be others and not require project/ family
    project = get_project_and_check_permissions(request.GET.get('projectGuid'), request.user)
    base_project = find_matching_xbrowse_model(project)
    family = Family.objects.get(guid=request.GET.get('familyGuid'))

    search_hash = request.GET.get('searchHash')
    search_spec_dict, variants = cache_utils.get_cached_results(base_project.project_id, search_hash)
    search_spec = MendelianVariantSearchSpec.fromJSON(search_spec_dict)
    if variants is None:
        variants = api_utils.calculate_mendelian_variant_search(search_spec, family, user=request.user)
    else:
        variants = [Variant.fromJSON(v) for v in variants]
        for variant in variants:
            variant.set_extra('family_id', family.family_id)

    add_extra_info_to_variants_project(get_reference(), base_project, variants, add_populations=True)

    parsed_variants = [_parsed_variant_json(v.toJSON(), request.user) for v in variants]
    genes = _saved_variant_genes(parsed_variants)
    _add_locus_lists(project, parsed_variants, genes)
    _add_saved_variants(parsed_variants, project, family)

    return create_json_response({
        'searchedVariants': [{'variantId': v['variantId']} if v['variantId'] else v for v in parsed_variants],
        'savedVariants': {variant['variantId']: variant for variant in parsed_variants if variant['variantId']},
        'genesById': genes,
    })


def _parsed_variant_json(variant_json, user):
    parsed_json = _variant_details(variant_json, user)
    parsed_json.update({field: variant_json[field] for field in ['xpos', 'ref', 'alt', 'pos']})
    parsed_json['chrom'] = variant_json['chr']
    return parsed_json


def _add_saved_variants(variants, project, family):
    for variant in variants:
        saved_variant = SavedVariant.objects.filter(
            xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'], project=project, family=family
        ).first()
        variant.update({
            'variantId': saved_variant.guid if saved_variant else None,
            'projectGuid': project.guid,
            'familyGuid': family.guid,
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


def _add_variant_filters(es):
    """
           self.variant_types = kwargs.get('variant_types')
        self.so_annotations = kwargs.get('so_annotations')  # todo: rename (and refactor)
        self.annotations = kwargs.get('annotations', {})
        self.ref_freqs = kwargs.get('ref_freqs')
        self.locations = kwargs.get('locations')
        self.genes = kwargs.get('genes')
        self.exclude_genes = kwargs.get('exclude_genes')
    :param es:
    :return:
    """

def _add_genotype_filters(es):
    pass


"""
Current search API:
    project_id:rare_genomes_project
    family_id:RGP_23
    search_mode:custom_inheritance
    variant_filter:{
        "so_annotations":["stop_gained","splice_donor_variant","splice_acceptor_variant","stop_lost","initiator_codon_variant","start_lost","missense_variant","protein_altering_variant","frameshift_variant","inframe_insertion","inframe_deletion"],
        "ref_freqs":[["1kg_wgs_phase3",0.0005],["1kg_wgs_phase3_popmax",0.001],["exac_v3",0.001],["exac_v3_popmax",0.0005],["gnomad_exomes",0.0005],["gnomad_exomes_popmax",0.0005],["gnomad_genomes",0.001],["gnomad_genomes_popmax",0.0005],["topmed",0.01]],
        "annotations":{},
    },
    quality_filter:{"min_gq":0,"min_ab":0},
    genotype_filter:{"RGP_23_1":"ref_alt","RGP_23_2":"alt_alt","RGP_23_3":"has_alt"},


"""

"""
individuals:
    - projects, projectGroups
    - families, familyGroups

datasets:
    - WES_variants, WGS_variants, WES_CNVs, WGS_CNVs

loci:
    - genes, transcripts, ranges, geneLists

allele info:
    - VEP annotation, consequence, clinvar

genotypes:
    - inheritance mode =>
    - allele balance, GQ, DP
"""