import logging
import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Sample, SavedVariant, VariantTagType, VariantTag, VariantNote, VariantFunctionalData,\
    LocusListInterval, LocusListGene, Family, CAN_VIEW, CAN_EDIT
from seqr.model_utils import create_seqr_model, delete_seqr_model
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.locus_list_api import get_project_locus_list_models
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variant, get_json_for_variant_tag, \
    get_json_for_variant_functional_data, get_json_for_variant_note
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from seqr.views.utils.variant_utils import update_project_saved_variant_json
from seqr.utils.xpos_utils import get_chrom_pos


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
    if request.GET.get('families'):
        variant_query = variant_query.filter(family__guid__in=request.GET.get('families').split(','))
    if variant_guid:
        variant_query = variant_query.filter(guid=variant_guid)
        if variant_query.count() < 1:
            return create_json_response({}, status=404, reason='Variant {} not found'.format(variant_guid))
    for saved_variant in variant_query:
        if saved_variant.varianttag_set.count() or saved_variant.variantnote_set.count():
            variant = get_json_for_saved_variant(saved_variant, add_tags=True, project_guid=project_guid)
            variant_json = variant_details(json.loads(saved_variant.saved_variant_json or '{}'), project, request.user)
            variant_json.update(variant)
            variants[saved_variant.guid] = variant_json

    genes = _saved_variant_genes(variants.values())
    _add_locus_lists(project, variants.values(), genes)

    return create_json_response({
        'savedVariantsByGuid': variants,
        'genesById': genes,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_saved_variant_handler(request):
    variant_json = json.loads(request.body)
    family_guid = variant_json.pop('familyGuid')
    non_variant_json = {
        k: variant_json.pop(k, None) for k in ['searchHash', 'tags', 'functionalData', 'notes', 'note', 'submitToClinvar']
    }

    family = Family.objects.get(guid=family_guid)
    check_permissions(family.project, request.user, CAN_VIEW)

    xpos = variant_json['xpos']
    ref = variant_json['ref']
    alt = variant_json['alt']
    # TODO remove project field from saved variants
    saved_variant = SavedVariant.objects.create(
        xpos=xpos,
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        project=family.project,
        saved_variant_json=json.dumps(variant_json)
    )

    if non_variant_json.get('note'):
        _create_variant_note(saved_variant, non_variant_json, request.user)
    elif non_variant_json.get('tags'):
        _create_new_tags(saved_variant, non_variant_json, request.user)

    variant_json.update(get_json_for_saved_variant(saved_variant, add_tags=True, project_guid=family.project.guid))
    return create_json_response({
        'savedVariantsByGuid': {saved_variant.guid: variant_json},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_variant_note_handler(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)

    _create_variant_note(saved_variant, json.loads(request.body), request.user)

    return create_json_response({'savedVariantsByGuid': {variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }}})


def _create_variant_note(saved_variant, note_json, user):
    create_seqr_model(
        VariantNote,
        saved_variant=saved_variant,
        note=note_json.get('note'),
        submit_to_clinvar=note_json.get('submitToClinvar') or False,
        search_hash=note_json.get('searchHash'),
        created_by=user,
    )


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, allow_unknown_keys=True)

    return create_json_response({'savedVariantsByGuid': {variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_VIEW)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)
    delete_seqr_model(note)
    return create_json_response({'savedVariantsByGuid': {variant_guid: {
        'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()]
    }}})


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

    for tag in saved_variant.varianttag_set.exclude(guid__in=existing_tag_guids):
        delete_seqr_model(tag)

    _create_new_tags(saved_variant, request_json, request.user)

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
                search_hash=request_json.get('searchHash'),
                created_by=request.user,
            )

    return create_json_response({'savedVariantsByGuid': {
        variant_guid: {
            'tags': [get_json_for_variant_tag(tag) for tag in saved_variant.varianttag_set.all()],
            'functionalData': [get_json_for_variant_functional_data(tag) for tag in saved_variant.variantfunctionaldata_set.all()]
        }
    }})


def _create_new_tags(saved_variant, tags_json, user):
    tags = tags_json.get('tags', [])
    new_tags = [tag for tag in tags if not tag.get('tagGuid')]

    for tag in new_tags:
        variant_tag_type = VariantTagType.objects.get(
            Q(name=tag['name']),
            Q(project=saved_variant.project) | Q(project__isnull=True)
        )
        create_seqr_model(
            VariantTag,
            saved_variant=saved_variant,
            variant_tag_type=variant_tag_type,
            search_hash=tags_json.get('searchHash'),
            created_by=user,
        )


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_saved_variant_json(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    updated_saved_variant_guids = update_project_saved_variant_json(project)

    return create_json_response({variant_guid: None for variant_guid in updated_saved_variant_guids})


# TODO process data before saving and then get rid of this
def variant_details(variant_json, project, user):
    if variant_json.get('mainTranscript'):
        return variant_json

    annotation = variant_json.get('annotation') or {}
    main_transcript = annotation.get('main_transcript') or (annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get('worst_vep_annotation_index') is not None and annotation['vep_annotation'] else {})
    is_es_variant = annotation.get('db') == 'elasticsearch'

    chrom, pos = get_chrom_pos(variant_json['xpos'])

    extras = variant_json.get('extras') or {}
    genome_version = extras.get('genome_version') or '37'
    lifted_over_genome_version = '37' if genome_version == '38' else '38'
    coords_field = 'grch%s_coords' % lifted_over_genome_version
    coords = extras.get(coords_field).split('-') if extras.get(coords_field) else []
    lifted_over_chrom = coords[0].lstrip('chr') if len(coords) > 0 else ''
    lifted_over_pos = coords[1] if len(coords) > 1 else ''

    genotypes = {
        sample_id: {
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
        } for sample_id, genotype in variant_json.get('genotypes', {}).items()
    }
    sample_guids_by_id = {s.sample_id: s.guid for s in Sample.objects.filter(
        individual__family__project=project,
        sample_id__in=genotypes.keys(),
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS
    )}
    genotypes = {sample_guids_by_id.get(sample_id): genotype for sample_id, genotype in genotypes.items()
                 if sample_guids_by_id.get(sample_id)}

    transcripts = defaultdict(list)
    for i, vep_a in enumerate(annotation['vep_annotation'] or []):
        # ,
        transcripts[vep_a.get('gene', vep_a.get('gene_id'))].append(
            _transcript_detail(vep_a, i == annotation.get('worst_vep_annotation_index')))

    return {
        'chrom': chrom,
        'pos': pos,
        'predictions': {
            'cadd': annotation.get('cadd_phred'),
            'dann': annotation.get('dann_score'),
            'eigen': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'gerp_rs': annotation.get('GERP_RS'),
            'phastcons_100_vert': annotation.get('phastCons100way_vertebrate'),
            'mpc': annotation.get('mpc_score'),
            'metasvm': annotation.get('metasvm'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'primate_ai': annotation.get('primate_ai_score'),
            'revel': annotation.get('revel_score'),
            'sift': annotation.get('sift'),
        },
        'mainTranscript': _transcript_detail(main_transcript, True),
        'clinvar': {
            'clinsig': extras.get('clinvar_clinsig'),
            'variantId': extras.get('clinvar_variant_id'),
            'alleleId': extras.get('clinvar_allele_id'),
            'goldStars': extras.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class') if (user and user.is_staff) else None,
        },
        'genotypes': genotypes,
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'locusLists': [],
        'originalAltAlleles': extras.get('orig_alt_alleles', []),
        'populations': {
            'callset': {
                'af': annotation.get('freqs', {}).get('AF'),
                'ac': annotation.get('pop_counts', {}).get('AC'),
                'an': annotation.get('pop_counts', {}).get('AN'),
            },
            'topmed': {
                'af': annotation.get('freqs', {}).get('topmed_AF'),
                'ac': annotation.get('pop_counts', {}).get('topmed_AC'),
                'an': annotation.get('pop_counts', {}).get('topmed_AN'),
            },
            'g1k': {
                'af': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'ac': annotation.get('pop_counts', {}).get('g1kAC'),
                'an': annotation.get('pop_counts', {}).get('g1kAN'),
            },
            'exac': {
                'af': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'ac': annotation.get('pop_counts', {}).get('exac_v3_AC'),
                'an':  annotation.get('pop_counts', {}).get('exac_v3_AN'),
                'hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
            },
            'gnomad_exomes': {
                'af': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax', annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_exomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
            },
            'gnomad_genomes': {
                'af': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_genomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
        },
        'rsid': annotation.get('rsid'),
        'transcripts': transcripts,
    }


def _transcript_detail(transcript, isChosenTranscript):
    return {
        'transcriptId': transcript.get('feature') or transcript.get('transcript_id'),
        'transcriptRank': 0 if isChosenTranscript else 1,
        'geneId': transcript.get('gene') or transcript.get('gene_id'),
        'geneSymbol': transcript.get('gene_symbol') or transcript.get('symbol'),
        'lof': transcript.get('lof'),
        'lofFlags': transcript.get('lof_flags'),
        'lofFilter': transcript.get('lof_filter'),
        'aminoAcids': transcript.get('amino_acids'),
        'biotype': transcript.get('biotype'),
        'canonical': transcript.get('canonical'),
        'cdnaPosition': transcript.get('cdna_position') or transcript.get('cdna_start'),
        'codons': transcript.get('codons'),
        'majorConsequence': transcript.get('consequence') or transcript.get('major_consequence'),
        'hgvsc': transcript.get('hgvsc'),
        'hgvsp': transcript.get('hgvsp'),
    }


def _saved_variant_genes(variants):
    gene_ids = set()
    for variant in variants:
        gene_ids.update(variant['transcripts'].keys())
    genes = get_genes(gene_ids, add_dbnsfp=True, add_omim=True, add_constraints=True)
    for gene in genes.values():
        if gene:
            gene['locusLists'] = []
    return genes


def _add_locus_lists(project, variants, genes):
    locus_lists = get_project_locus_list_models(project)
    for variant in variants:
        variant['locusLists'] = []

    locus_list_intervals_by_chrom = defaultdict(list)
    for interval in LocusListInterval.objects.filter(locus_list__in=locus_lists):
        locus_list_intervals_by_chrom[interval.chrom].append(interval)
    if locus_list_intervals_by_chrom:
        for variant in variants:
            for interval in locus_list_intervals_by_chrom[variant['chrom']]:
                pos = variant['pos'] if variant['genomeVersion'] == interval.genome_version else variant['liftedOverPos']
                if pos and interval.start <= int(pos) <= interval.end:
                    variant['locusLists'].append(interval.locus_list.name)

    for locus_list_gene in LocusListGene.objects.filter(locus_list__in=locus_lists, gene_id__in=genes.keys()):
        genes[locus_list_gene.gene_id]['locusLists'].append(locus_list_gene.locus_list.name)