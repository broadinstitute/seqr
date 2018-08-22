import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Family, Individual, SavedVariant
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _variant_details, _saved_variant_genes, _add_locus_lists
from seqr.views.pages.project_page import _get_json_for_variant_tag_types
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    get_json_for_variant_tag, get_json_for_variant_functional_data, get_json_for_variant_note, _get_json_for_family, \
    _get_json_for_project, _get_json_for_individuals
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.model_utils import find_matching_xbrowse_model


from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.api import utils as api_utils
from xbrowse_server.mall import get_reference, get_datastore
from xbrowse.analysis_modules.mendelian_variant_search import MendelianVariantSearchSpec


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants_handler(request):
    """Search variants.
    """

    # TODO this is only mendelian variant search, should be others and not require project/ family
    project = get_project_and_check_permissions(request.GET.get('projectGuid'), request.user)
    family = Family.objects.get(guid=request.GET.get('familyGuid'))

    variant_filter = {}
    if request.GET.get('freqs'):
        freqs = json.loads(request.GET.get('freqs'))
        variant_filter['ref_freqs'] = [[k, v['af']] for k, v in freqs.items() if v.get('af') is not None]
        variant_filter['ref_acs'] = [[k, v['ac']] for k, v in freqs.items() if v.get('ac') is not None and not v.get('af')]
        variant_filter['ref_hom_hemi'] = [[k, v['hh']] for k, v in freqs.items() if v.get('hh') is not None]
    if request.GET.get('annotations'):
        variant_filter['so_annotations'] = request.GET.get('annotations').split(',')
    search_spec = MendelianVariantSearchSpec.fromJSON({
        'family_id': family.family_id,
        'search_mode': request.GET.get('searchMode'),
        'inheritance_mode': request.GET.get('inheritance'),
        'genotype_inheritance_filter': json.loads(request.GET.get('genotypeInheritanceFilter', '{}')),
        'gene_burden_filter': json.loads(request.GET.get('genotypeInheritanceFilter', '{}')),
        'variant_filter': variant_filter,
        'quality_filter': json.loads(request.GET.get('qualityFilter', '{}')),
        'allele_count_filter': json.loads(request.GET.get('alleleCountFilter', '{}')),
    })

    variants = api_utils.calculate_mendelian_variant_search(search_spec, find_matching_xbrowse_model(family), user=request.user)
    add_extra_info_to_variants_project(get_reference(), find_matching_xbrowse_model(project), variants, add_populations=True)

    parsed_variants = [_parsed_variant_json(v.toJSON(), request.user) for v in variants]
    genes = _saved_variant_genes(parsed_variants)
    _add_locus_lists(project, parsed_variants, genes)
    _add_saved_variants(parsed_variants, project, family)

    project_json = _get_json_for_project(project, request.user)
    project_json.update(_get_json_for_variant_tag_types(project))
    family_json = _get_json_for_family(family, user=request.user, project_guid=project.guid, add_individual_guids_field=True)
    individuals = Individual.objects.filter(guid__in=family_json['individualGuids'])
    individuals_json = _get_json_for_individuals(
        individuals, user=request.user, project_guid=project.guid, family_guid=family.guid
    )

    return create_json_response({
        'searchedVariants': [{'variantGuid': v['variantGuid']} if v['variantGuid'] else v for v in parsed_variants],
        'savedVariantsByGuid': {variant['variantGuid']: variant for variant in parsed_variants if variant['variantGuid']},
        'genesById': genes,
        'projectsByGuid': {project.guid: project_json},
        'familiesByGuid': {family.guid: family_json},
        'individualsByGuid': {i['individualGuid']: i for i in individuals_json}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def variant_transcripts(request):
    project = get_project_and_check_permissions(request.GET.get('projectGuid'), request.user)
    family = Family.objects.get(guid=request.GET.get('familyGuid'))

    base_project = find_matching_xbrowse_model(project)
    loaded_variant = get_datastore(base_project).get_single_variant(
        base_project.project_id,
        family.family_id,
        int(request.GET.get('xpos')),
        request.GET.get('ref'),
        request.GET.get('alt'),
    )

    return create_json_response({'transcripts': _parsed_variant_transcripts(loaded_variant.annotation)})


def _parsed_variant_json(variant_json, user):
    parsed_json = _variant_details(variant_json, user)
    parsed_json.update({field: variant_json[field] for field in ['xpos', 'ref', 'alt', 'pos']})
    parsed_json['chrom'] = variant_json['chr']
    return parsed_json


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


def _add_saved_variants(variants, project, family):
    for variant in variants:
        saved_variant = SavedVariant.objects.filter(
            xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'], project=project, family=family
        ).first()
        variant.update({
            'variantId': '{}-{}-{}'.format(variant['xpos'], variant['ref'], variant['alt']),  # TODO may not be unique in non-family speific searches
            'variantGuid': saved_variant.guid if saved_variant else None,
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