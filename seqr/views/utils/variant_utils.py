from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
import logging
import redis

from matchmaker.models import MatchmakerSubmissionGenes, MatchmakerSubmission
from reference_data.models import TranscriptInfo
from seqr.models import SavedVariant, VariantSearchResults, Family, LocusList, LocusListInterval, LocusListGene, \
    RnaSeqTpm, PhenotypePrioritization, Project, Sample, VariantTagType
from seqr.utils.search.utils import get_variants_for_variant_ids
from seqr.utils.gene_utils import get_genes_for_variants
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_discovery_tags, get_json_for_locus_lists, \
    get_json_for_queryset, get_json_for_rna_seq_outliers, get_json_for_saved_variants_with_tags, \
    get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import has_case_review_permissions, user_is_analyst
from seqr.views.utils.project_context_utils import add_project_tag_types, add_families_context
from settings import REDIS_SERVICE_HOSTNAME, REDIS_SERVICE_PORT

logger = logging.getLogger(__name__)


MAX_VARIANTS_FETCH = 1000
DISCOVERY_CATEGORY = 'CMG Discovery Tags'


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
        variants_json += get_variants_for_variant_ids(families, sub_var_ids, user=user)

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
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, port=REDIS_SERVICE_PORT, socket_connect_timeout=3)
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


def _saved_variant_genes_transcripts(variants):
    family_genes = defaultdict(set)
    gene_ids = set()
    transcript_ids = set()
    for variant in variants:
        if not isinstance(variant, list):
            variant = [variant]
        for var in variant:
            for gene_id, transcripts in var.get('transcripts', {}).items():
                gene_ids.add(gene_id)
                transcript_ids.update([t['transcriptId'] for t in transcripts if t.get('transcriptId')])
            for family_guid in var['familyGuids']:
                family_genes[family_guid].update(var.get('transcripts', {}).keys())

    genes = get_genes_for_variants(gene_ids)
    for gene in genes.values():
        if gene:
            gene['locusListGuids'] = []

    transcripts = {
        t['transcriptId']: t for t in get_json_for_queryset(
            TranscriptInfo.objects.filter(transcript_id__in=transcript_ids),
            nested_fields=[{'fields': ('refseqtranscript', 'refseq_id'), 'key': 'refseqId'}]
        )
    }

    return genes, transcripts, family_genes


def _add_locus_lists(projects, genes, add_list_detail=False, user=None):
    locus_lists = LocusList.objects.filter(projects__in=projects)

    if add_list_detail:
        locus_lists_by_guid = {
            ll['locusListGuid']: dict(intervals=[], **ll)
            for ll in get_json_for_locus_lists(locus_lists, user)
        }
    else:
        locus_lists_by_guid = defaultdict(lambda: {'intervals': []})
    intervals = LocusListInterval.objects.filter(locus_list__in=locus_lists)
    for interval in get_json_for_queryset(intervals, nested_fields=[{'fields': ('locus_list', 'guid')}]):
        locus_lists_by_guid[interval['locusListGuid']]['intervals'].append(interval)

    for locus_list_gene in LocusListGene.objects.filter(locus_list__in=locus_lists, gene_id__in=genes.keys()).prefetch_related('locus_list', 'palocuslistgene'):
        gene_json = genes[locus_list_gene.gene_id]
        locus_list_guid = locus_list_gene.locus_list.guid
        gene_json['locusListGuids'].append(locus_list_guid)
        _add_pa_detail(locus_list_gene, locus_list_guid, gene_json)

    return locus_lists_by_guid


def _get_rna_seq_outliers(gene_ids, sample_ids):
    filters = {'gene_id__in': gene_ids, 'sample_id__in': sample_ids}

    return get_json_for_rna_seq_outliers(filters)


def get_phenotype_prioritization(family_guids, gene_ids=None):
    data_by_individual_gene = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    gene_filter = {'gene_id__in': gene_ids} if gene_ids is not None else {}
    data_dicts = get_json_for_queryset(
        PhenotypePrioritization.objects.filter(
            individual__family__guid__in=family_guids, rank__lte=10, **gene_filter).order_by('disease_id'),
        nested_fields=[{'fields': ('individual', 'guid'), 'key': 'individualGuid'}],
    )

    for data in data_dicts:
        data_by_individual_gene[data.pop('individualGuid')][data.pop('geneId')][data.pop('tool')].append(data)

    return data_by_individual_gene


def _get_family_has_rna_tpm(family_genes, gene_ids, sample_family_map):
    tpm_family_genes = RnaSeqTpm.objects.filter(
        sample_id__in=sample_family_map.keys(), gene_id__in=gene_ids,
    ).values('sample_id').annotate(genes=ArrayAgg('gene_id', distinct=True))
    family_tpms = defaultdict(lambda: {'tpmGenes': []})
    for agg in tpm_family_genes.iterator():
        family_guid = sample_family_map[agg['sample_id']]
        genes = [gene for gene in agg['genes'] if gene in family_genes[family_guid]]
        if genes:
            family_tpms[family_guid]['tpmGenes'] += genes
    return family_tpms


def _add_discovery_tags(variants, discovery_tags):
    for variant in variants:
        tags = discovery_tags.get(get_variant_key(**variant))
        if tags:
            if not variant.get('discoveryTags'):
                variant['discoveryTags'] = []
            variant['discoveryTags'] += [tag for tag in tags if tag['savedVariant']['familyGuid'] not in variant['familyGuids']]


def _add_pa_detail(locus_list_gene, locus_list_guid, gene_json):
    if hasattr(locus_list_gene, 'palocuslistgene'):
        if not gene_json.get('panelAppDetail'):
            gene_json['panelAppDetail'] = {}
        gene_json['panelAppDetail'][locus_list_guid] = {
            'confidence': locus_list_gene.palocuslistgene.confidence_level,
            'moi': locus_list_gene.palocuslistgene.mode_of_inheritance,
        }


LOAD_PROJECT_TAG_TYPES_CONTEXT_PARAM = 'loadProjectTagTypes'
LOAD_FAMILY_CONTEXT_PARAM = 'loadFamilyContext'


def get_variants_response(request, saved_variants, response_variants=None, add_all_context=False, include_igv=True,
                          add_locus_list_detail=False, include_individual_gene_scores=True, include_project_name=False):
    response = get_json_for_saved_variants_with_tags(saved_variants, add_details=True) \
        if saved_variants is not None else {'savedVariantsByGuid': {}}

    variants = list(response['savedVariantsByGuid'].values()) if response_variants is None else response_variants
    genes, transcripts, family_genes = _saved_variant_genes_transcripts(variants)

    projects = Project.objects.filter(family__guid__in=family_genes.keys()).distinct()
    project = list(projects)[0] if len(projects) == 1 else None

    discovery_tags = None
    is_analyst = user_is_analyst(request.user)
    if is_analyst:
        discovery_tags, discovery_response = get_json_for_discovery_tags(response['savedVariantsByGuid'].values(), request.user)
        response.update(discovery_response)

    response['transcriptsById'] = transcripts
    response['locusListsByGuid'] = _add_locus_lists(
        projects, genes, add_list_detail=add_locus_list_detail, user=request.user)

    if discovery_tags:
        _add_discovery_tags(variants, discovery_tags)
    response['genesById'] = genes

    mme_submission_genes = MatchmakerSubmissionGenes.objects.filter(
        saved_variant__guid__in=response['savedVariantsByGuid'].keys()).values(
        geneId=F('gene_id'), variantGuid=F('saved_variant__guid'), submissionGuid=F('matchmaker_submission__guid'))
    for s in mme_submission_genes:
        response_variant = response['savedVariantsByGuid'][s['variantGuid']]
        if 'mmeSubmissions' not in response_variant:
            response_variant['mmeSubmissions'] = []
        response_variant['mmeSubmissions'].append(s)

    submissions = get_json_for_matchmaker_submissions(MatchmakerSubmission.objects.filter(
        matchmakersubmissiongenes__saved_variant__guid__in=response['savedVariantsByGuid'].keys()))
    response['mmeSubmissionsByGuid'] = {s['submissionGuid']: s for s in submissions}

    rna_tpm = None
    if include_individual_gene_scores:
        present_family_genes = {k: v for k, v in family_genes.items() if v}
        rna_sample_family_map = dict(Sample.objects.filter(
            individual__family__guid__in=present_family_genes.keys(), sample_type=Sample.SAMPLE_TYPE_RNA, is_active=True,
        ).values_list('id', 'individual__family__guid'))
        response['rnaSeqData'] = _get_rna_seq_outliers(genes.keys(), rna_sample_family_map.keys())
        rna_tpm = _get_family_has_rna_tpm(present_family_genes, genes.keys(), rna_sample_family_map)
        response['phenotypeGeneScores'] = get_phenotype_prioritization(present_family_genes.keys(), gene_ids=genes.keys())

    if add_all_context or request.GET.get(LOAD_PROJECT_TAG_TYPES_CONTEXT_PARAM) == 'true':
        project_fields = {'projectGuid': 'guid'}
        if include_project_name:
            project_fields['name'] = 'name'
        if include_igv:
            project_fields['genomeVersion'] = 'genome_version'
        response['projectsByGuid'] = {project.guid: {k: getattr(project, field) for k, field in project_fields.items()} for project in projects}
        add_project_tag_types(response['projectsByGuid'])

    if add_all_context or request.GET.get(LOAD_FAMILY_CONTEXT_PARAM) == 'true':
        families = Family.objects.filter(guid__in=family_genes.keys())
        add_families_context(
            response, families, project_guid=project.guid if project else None, user=request.user, is_analyst=is_analyst,
            has_case_review_perm=bool(project) and has_case_review_permissions(project, request.user), include_igv=include_igv,
        )

        if rna_tpm:
            for family_guid, data in rna_tpm.items():
                response['familiesByGuid'][family_guid].update(data)

    return response


def get_variant_main_transcript(variant):
    main_transcript_id = variant.get('selectedMainTranscriptId') or variant.get('mainTranscriptId')
    if main_transcript_id:
        for gene_id, transcripts in variant.get('transcripts', {}).items():
            main_transcript = next((t for t in transcripts if t['transcriptId'] == main_transcript_id), None)
            if main_transcript:
                if 'geneId' not in main_transcript:
                    main_transcript['geneId'] = gene_id
                return main_transcript
    elif len(variant.get('transcripts', {})) == 1:
        gene_id = next(k for k in variant['transcripts'].keys())
        #  Handle manually created SNPs
        if variant['transcripts'][gene_id] == []:
            return {'geneId': gene_id}
    return {}


def get_sv_name(variant_json):
    return variant_json.get('svName') or '{svType}:chr{chrom}:{pos}-{end}'.format(**variant_json)


def get_saved_discovery_variants_by_family(variant_filter, format_variants, get_family_id):
    tag_types = VariantTagType.objects.filter(project__isnull=True, category=DISCOVERY_CATEGORY)

    project_saved_variants = SavedVariant.objects.filter(
        varianttag__variant_tag_type__in=tag_types,
        **variant_filter,
    ).order_by('created_date').distinct()

    project_saved_variants = format_variants(project_saved_variants, tag_types)

    saved_variants_by_family = defaultdict(list)
    for saved_variant in project_saved_variants:
        family_id = get_family_id(saved_variant)
        saved_variants_by_family[family_id].append(saved_variant)

    return saved_variants_by_family


HET = 'Heterozygous'
HOM_ALT = 'Homozygous'
HEMI = 'Hemizygous'


def get_variant_inheritance_models(variant_json, affected_individual_guids, unaffected_individual_guids, male_individual_guids):
    inheritance_models = set()

    affected_indivs_with_hom_alt_variants = set()
    affected_indivs_with_het_variants = set()
    unaffected_indivs_with_het_variants = set()
    is_x_linked = False

    genotypes = variant_json.get('genotypes')
    if genotypes:
        chrom = variant_json['chrom']
        is_x_linked = "X" in chrom
        for sample_guid, genotype in genotypes.items():
            zygosity = get_genotype_zygosity(genotype, is_hemi_variant=is_x_linked and sample_guid in male_individual_guids)
            if zygosity in (HOM_ALT, HEMI) and sample_guid in unaffected_individual_guids:
                # No valid inheritance modes for hom alt unaffected individuals
                return set(), set()

            if zygosity in (HOM_ALT, HEMI) and sample_guid in affected_individual_guids:
                affected_indivs_with_hom_alt_variants.add(sample_guid)
            elif zygosity == HET and sample_guid in affected_individual_guids:
                affected_indivs_with_het_variants.add(sample_guid)
            elif zygosity == HET and sample_guid in unaffected_individual_guids:
                unaffected_indivs_with_het_variants.add(sample_guid)

    # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
    if affected_indivs_with_hom_alt_variants:
        if is_x_linked:
            inheritance_models.add("X-linked")
        else:
            inheritance_models.add("AR-homozygote")

    if not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
        if unaffected_individual_guids:
            inheritance_models.add("de novo")
        else:
            inheritance_models.add("AD")

    potential_compound_het_gene_ids = set()
    if (len(unaffected_individual_guids) < 2 or unaffected_indivs_with_het_variants) \
            and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants \
            and 'transcripts' in variant_json:
        potential_compound_het_gene_ids.update(list(variant_json['transcripts'].keys()))

    return inheritance_models, potential_compound_het_gene_ids


def get_genotype_zygosity(genotype, is_hemi_variant):
    num_alt = genotype.get('numAlt')
    cn = genotype.get('cn')
    if num_alt == 2 or cn == 0 or (cn != None and cn > 3):
        return HOM_ALT
    if num_alt == 1 or cn == 1 or cn == 3:
        return HEMI if is_hemi_variant else HET
    return None


DISCOVERY_PHENOTYPE_CLASSES = {
    'NEW': ['Tier 1 - Known gene, new phenotype', 'Tier 2 - Known gene, new phenotype'],
    'EXPAN': ['Tier 1 - Phenotype expansion', 'Tier 1 - Novel mode of inheritance', 'Tier 2 - Phenotype expansion'],
    'UE': ['Tier 1 - Phenotype not delineated', 'Tier 2 - Phenotype not delineated'],
    'KNOWN': ['Known gene for phenotype'],
}


def get_discovery_phenotype_class(variant_tag_names):
    for phenotype_class, class_tag_names in DISCOVERY_PHENOTYPE_CLASSES.items():
        if any(tag in variant_tag_names for tag in class_tag_names):
            return phenotype_class
    return None
