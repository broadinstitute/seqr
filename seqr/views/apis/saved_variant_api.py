import logging
import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import SavedVariant, VariantTagType, VariantTag, VariantNote, VariantFunctionalData,\
    LocusListInterval, LocusListGene, CAN_VIEW
from seqr.model_utils import create_seqr_model, delete_seqr_model, find_matching_xbrowse_model
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.locus_list_api import get_project_locus_list_models
from seqr.views.utils.gene_utils import get_genes
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variant, get_json_for_variant_tag, \
    get_json_for_variant_functional_data, get_json_for_variant_note
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from xbrowse_server.mall import get_datastore

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def saved_variant_data(request, project_guid, variant_guid=None):
    project = get_project_and_check_permissions(project_guid, request.user)

    variants = {}
    variant_query = SavedVariant.objects.filter(project=project)\
        .select_related('family')\
        .only('xpos_start', 'ref', 'alt', 'saved_variant_json', 'family__guid', 'guid')\
        .prefetch_related('varianttag_set', 'varianttag_set__created_by', 'varianttag_set__variant_tag_type',
                          'variantfunctionaldata_set', 'variantfunctionaldata_set__created_by', 'variantnote_set',
                          'variantnote_set__created_by')
    if request.GET.get('family'):
        variant_query = variant_query.filter(family__guid=request.GET.get('family'))
    if variant_guid:
        variant_query = variant_query.filter(guid=variant_guid)
        if variant_query.count() < 1:
            return create_json_response({}, status=404, reason='Variant {} not found'.format(variant_guid))
    for saved_variant in variant_query:
        variant = get_json_for_saved_variant(saved_variant, add_tags=True)
        if variant['tags'] or variant['notes']:
            variant_json = json.loads(saved_variant.saved_variant_json or '{}')
            logger.info(variant_json)
            variant.update(_variant_details(variant_json, request.user))
            variants[variant['variantId']] = variant

    genes = _saved_variant_genes(variants)
    _add_locus_lists(project, variants, genes)

    return create_json_response({
        'savedVariants': variants,
        'genesById': genes,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def saved_variant_transcripts(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)

    # TODO when variant search is rewritten for seqr models use that here
    base_project = find_matching_xbrowse_model(saved_variant.project)
    loaded_variant = get_datastore(base_project).get_single_variant(
        base_project.project_id,
        saved_variant.family.family_id,
        saved_variant.xpos,
        saved_variant.ref,
        saved_variant.alt,
    )

    return create_json_response({variant_guid: {'transcripts': _variant_transcripts(loaded_variant.annotation)}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_variant_note_handler(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)

    request_json = json.loads(request.body)
    create_seqr_model(
        VariantNote,
        saved_variant=saved_variant,
        note=request_json.get('note'),
        submit_to_clinvar=request_json.get('submitToClinvar', False),
        search_parameters=request_json.get('searchParameters'),
        created_by=request.user,
    )

    return create_json_response({variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, allow_unknown_keys=True)

    return create_json_response({variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)
    delete_seqr_model(note)
    return create_json_response({variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_tags_handler(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)

    request_json = json.loads(request.body)
    updated_tags = request_json.get('tags', [])
    updated_functional_data = request_json.get('functionalData', [])

    # Update tags

    existing_tag_guids = [tag['tagGuid'] for tag in updated_tags if tag.get('tagGuid')]
    new_tags = [tag for tag in updated_tags if not tag.get('tagGuid')]

    for tag in saved_variant.varianttag_set.exclude(guid__in=existing_tag_guids):
        delete_seqr_model(tag)

    for tag in new_tags:
        variant_tag_type = VariantTagType.objects.get(
            Q(name=tag['name']),
            Q(project=saved_variant.project) | Q(project__isnull=True)
        )
        create_seqr_model(
            VariantTag,
            saved_variant=saved_variant,
            variant_tag_type=variant_tag_type,
            search_parameters=request_json.get('searchParameters'),
            created_by=request.user,
        )

    # Update functional data

    existing_functional_guids = [tag['tagGuid'] for tag in updated_functional_data if tag.get('tagGuid')]

    for tag in saved_variant.variantfunctionaldata_set.exclude(guid__in=existing_functional_guids):
        delete_seqr_model(tag)

    for tag in updated_functional_data:
        if tag.get('tagGuid'):
            tag_model = VariantFunctionalData.objects.get(
                guid=tag.get('tagGuid'),
                functional_data_tag=tag.get('name'),
                saved_variant=saved_variant
            )
            update_model_from_json(tag_model, tag, allow_unknown_keys=True)
        else:
            create_seqr_model(
                VariantFunctionalData,
                saved_variant=saved_variant,
                functional_data_tag=tag.get('name'),
                metadata=tag.get('metadata'),
                search_parameters=request_json.get('searchParameters'),
                created_by=request.user,
            )

    return create_json_response({
        variant_guid: {
            'tags': [get_json_for_variant_tag(tag) for tag in saved_variant.varianttag_set.all()],
            'functionalData': [get_json_for_variant_functional_data(tag) for tag in saved_variant.variantfunctionaldata_set.all()]
        }
    })


# TODO once variant search is rewritten saved_variant_json shouldn't need any postprocessing

def _variant_transcripts(annotation):
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


def _variant_details(variant_json, user):
    annotation = variant_json.get('annotation') or {}
    main_transcript = annotation.get('main_transcript') or (annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get('worst_vep_annotation_index') is not None and annotation['vep_annotation'] else None)
    is_es_variant = annotation.get('db') == 'elasticsearch'

    extras = variant_json.get('extras') or {}
    genome_version = extras.get('genome_version') or '37'
    lifted_over_genome_version = '37' if genome_version == '38' else '38'
    coords_field = 'grch%s_coords' % lifted_over_genome_version
    coords = extras.get(coords_field).split('-') if extras.get(coords_field) else []
    lifted_over_chrom = coords[0].lstrip('chr') if len(coords) > 0 else ''
    lifted_over_pos = coords[1] if len(coords) > 1 else ''

    return {
        'annotation': {
            'cadd_phred': annotation.get('cadd_phred'),
            'dann_score': annotation.get('dann_score'),
            'eigen_phred': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'freqs': {
                'AF': annotation.get('freqs', {}).get('AF'),
                'topmedAF': annotation.get('freqs', {}).get('topmed_AF'),
                'g1k': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'exac': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'gnomad_exomes': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax', annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'gnomad_genomes': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
            },
            'gerp_rs': annotation.get('GERP_RS'),
            'phastcons100vert': annotation.get('phastCons100way_vertebrate'),

            'mpc_score': annotation.get('mpc_score'),
            'metasvm': annotation.get('metasvm'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'popCounts': {
                'AC': annotation.get('pop_counts', {}).get('AC'),
                'AN': annotation.get('pop_counts', {}).get('AN'),
                'g1kAC': annotation.get('pop_counts', {}).get('g1kAC'),
                'g1kAN': annotation.get('pop_counts', {}).get('g1kAN'),
                'topmedAC': annotation.get('pop_counts', {}).get('topmed_AC'),
                'topmedAN': annotation.get('pop_counts', {}).get('topmed_AN'),
                'gnomadExomesAC': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'gnomadExomesAN': annotation.get('pop_counts', {}).get('gnomad_exomes_AN'),
                'gnomadGenomesAC': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'gnomadGenomesAN': annotation.get('pop_counts', {}).get('gnomad_genomes_AN'),
                'exacAC': annotation.get('pop_counts', {}).get('exac_v3_AC'),
                'exac_hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'exac_hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
                'exacAN': annotation.get('pop_counts', {}).get('exac_v3_AN'),
                'gnomad_exomes_hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'gnomad_exomes_hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
                'gnomad_genomes_hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'gnomad_genomes_hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
            'primate_ai_score': annotation.get('primate_ai_score'),
            'revel_score': annotation.get('revel_score'),
            'rsid': annotation.get('rsid'),
            'sift': annotation.get('sift'),
            'vepConsequence': annotation.get('vep_consequence'),
            'vepGroup': annotation.get('vep_group'),
            'mainTranscript': {
                'symbol': main_transcript.get('gene_symbol') or main_transcript.get('symbol'),
                'lof': main_transcript.get('lof'),
                'lofFlags': main_transcript.get('lof_flags'),
                'lofFilter': main_transcript.get('lof_filter'),
                'hgvsc': main_transcript.get('hgvsc'),
                'hgvsp': main_transcript.get('hgvsp'),
                'aminoAcids': main_transcript.get('amino_acids'),
                'proteinPosition': main_transcript.get('protein_position'),
            } if main_transcript else None,
        },
        'clinvar': {
            'clinsig': extras.get('clinvar_clinsig'),
            'variantId': extras.get('clinvar_variant_id'),
            'alleleId': extras.get('clinvar_allele_id'),
            'goldStars': extras.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class') if user.is_staff else None,
        },
        'geneIds': extras.get('genes', {}).keys(),
        'genotypes': {
            individual_id: {
                'ab': genotype.get('ab'),
                'ad': genotype.get('extras', {}).get('ad'),
                'alleles': genotype.get('alleles', []),
                'cnvs': {
                    'array': genotype.get('extras', {}).get('cnvs', {}).get('array'),
                    'caller': genotype.get('extras', {}).get('cnvs', {}).get('caller'),
                    'cn': genotype.get('extras', {}).get('cnvs', {}).get('cn'),
                    'freq': genotype.get('extras', {}).get('cnvs', {}).get('freq'),
                    'LRR_median': genotype.get('extras', {}).get('cnvs', {}).get('LRR_median'),
                    'LRR_sd': genotype.get('extras', {}).get('cnvs', {}).get('LRR_sd'),
                    'size': genotype.get('extras', {}).get('cnvs', {}).get('size'),
                    'snps': genotype.get('extras', {}).get('cnvs', {}).get('snps'),
                    'type': genotype.get('extras', {}).get('cnvs', {}).get('type'),
                },
                'dp': genotype.get('extras', {}).get('dp'),
                'filter': genotype.get('filter'),
                'gq': genotype.get('gq'),
                'numAlt': genotype.get('num_alt'),
                'pl': genotype.get('extras', {}).get('pl'),
            } for individual_id, genotype in variant_json.get('genotypes', {}).items()
        },
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'locusLists': [],
        'origAltAlleles': extras.get('orig_alt_alleles', []),
        'transcripts': _variant_transcripts(annotation) if annotation.get('vep_annotation') else None,
    }


def _saved_variant_genes(variants):
    gene_ids = set()
    for variant in variants.values():
        gene_ids.update(variant['geneIds'])
    genes = get_genes(gene_ids)
    for gene in genes.values():
        gene['locusLists'] = []
    return genes


def _add_locus_lists(project, variants, genes):
    locus_lists = get_project_locus_list_models(project)

    locus_list_intervals_by_chrom = defaultdict(list)
    for interval in LocusListInterval.objects.filter(locus_list__in=locus_lists):
        locus_list_intervals_by_chrom[interval.chrom].append(interval)
    if locus_list_intervals_by_chrom:
        for variant in variants.values():
            for interval in locus_list_intervals_by_chrom[variant['chrom']]:
                pos = variant['pos'] if variant['genomeVersion'] == interval.genome_version else variant['liftedOverPos']
                if pos and interval.start <= int(pos) <= interval.end:
                    variant['locusLists'].append(interval.locus_list.name)

    for locus_list_gene in LocusListGene.objects.filter(locus_list__in=locus_lists, gene_id__in=genes.keys()):
        genes[locus_list_gene.gene_id]['locusLists'].append(locus_list_gene.locus_list.name)