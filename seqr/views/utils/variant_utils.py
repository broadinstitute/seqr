from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
import logging
import redis

from matchmaker.models import MatchmakerSubmissionGenes, MatchmakerSubmission
from reference_data.models import TranscriptInfo
from seqr.models import SavedVariant, VariantSearchResults, Family, LocusList, LocusListInterval, LocusListGene, \
    RnaSeqTpm, PhenotypePrioritization, Project
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


def _get_rna_seq_outliers(gene_ids, family_guids):
    filters = {'gene_id__in': gene_ids, 'sample__individual__family__guid__in': family_guids}

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


def _get_family_has_rna_tpm(family_genes, gene_ids):
    tpm_family_genes = RnaSeqTpm.objects.filter(
        sample__individual__family__guid__in=family_genes.keys(), gene_id__in=gene_ids,
    ).values('sample__individual__family__guid').annotate(genes=ArrayAgg('gene_id', distinct=True))
    family_tpms = {}
    for agg in tpm_family_genes:
        family_guid = agg['sample__individual__family__guid']
        genes = [gene for gene in agg['genes'] if gene in family_genes[family_guid]]
        if genes:
            family_tpms[family_guid] = {'tpmGenes': genes}
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
    response = get_json_for_saved_variants_with_tags(saved_variants, add_details=True)

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
        response['rnaSeqData'] = _get_rna_seq_outliers(genes.keys(), present_family_genes.keys())
        rna_tpm = _get_family_has_rna_tpm(present_family_genes, genes.keys())
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
