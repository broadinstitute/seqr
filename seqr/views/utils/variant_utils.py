from collections import defaultdict
from clickhouse_backend.models import ArrayField, StringField
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Q, Count, prefetch_related_objects
import json
import logging
import redis

from clickhouse_search.backend.functions import ArrayDistinct, ArrayMap
from clickhouse_search.search import get_variants_queryset, get_clickhouse_genotypes
from matchmaker.models import MatchmakerSubmissionGenes, MatchmakerSubmission
from reference_data.models import TranscriptInfo, Omim, GENOME_VERSION_GRCh38
from seqr.models import SavedVariant, VariantSearchResults, Family, LocusList, LocusListInterval, LocusListGene, \
    RnaSeqTpm, PhenotypePrioritization, Project, Sample, RnaSample, VariantTag, VariantTagType
from seqr.utils.search.utils import variant_dataset_type
from seqr.utils.gene_utils import get_genes_for_variants
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.json_to_orm_utils import create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_discovery_tags, get_json_for_locus_lists, \
    get_json_for_queryset, get_json_for_rna_seq_outliers, get_json_for_saved_variants_with_tags, \
    get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import has_case_review_permissions, user_is_analyst
from seqr.views.utils.project_context_utils import add_project_tag_types, add_families_context
from settings import REDIS_SERVICE_HOSTNAME, REDIS_SERVICE_PORT

logger = logging.getLogger(__name__)


DISCOVERY_CATEGORY = 'CMG Discovery Tags'
OMIM_GENOME_VERSION = GENOME_VERSION_GRCh38


def parse_saved_variant_json(variant_json, family_id, variant_id=None, dataset_type=None):
    xpos = variant_json['xpos']
    ref = variant_json.get('ref')
    var_length = variant_json['end'] - variant_json['pos'] if variant_json.get('end') is not None else len(ref) - 1
    variant_id = variant_json.get('variantId', variant_id)
    gene_ids = sorted(
        variant_json['transcripts'].keys(), key=lambda gene_id: _transcript_sort(gene_id, variant_json)
    ) if 'transcripts' in variant_json else variant_json['gene_ids']
    return {
        'key': variant_json['key'],
        'xpos': xpos,
        'xpos_end': xpos + var_length,
        'ref': ref,
        'alt': variant_json.get('alt'),
        'family_id': family_id,
        'variant_id': variant_id,
        'genotypes': variant_json.get('genotypes', {}),
        'dataset_type': dataset_type or variant_dataset_type({'variantId': variant_id, **variant_json}),
        'gene_ids': gene_ids,
    }


def _transcript_sort(gene_id, saved_variant_json):
    gene_transcripts = saved_variant_json['transcripts'][gene_id]
    main_transcript_id = saved_variant_json.get('mainTranscriptId')
    is_main_gene = bool(main_transcript_id) and any(t.get('transcriptId') == main_transcript_id for t in gene_transcripts)
    return (not is_main_gene, min(t.get('transcriptRank', 100) for t in gene_transcripts) if gene_transcripts else 100)


def bulk_create_tagged_variants(family_variant_data, tag_name, get_metadata, user, project=None, get_comp_het_metadata=None, load_new_variant_data=False, remove_missing_metadata=True, primary_id_field='variant_id', dataset_type=None, **kwargs):
    all_family_ids = {family_id for family_id, _ in family_variant_data.keys()}
    all_variant_ids = {variant_id for _, variant_id in family_variant_data.keys()}

    saved_variant_map = {
        (v.family_id, getattr(v, primary_id_field)): v
        for v in SavedVariant.objects.filter(**{'family_id__in':all_family_ids, f'{primary_id_field}__in': all_variant_ids})
    }

    new_variant_keys = set(family_variant_data.keys()) - set(saved_variant_map.keys())
    if new_variant_keys:
        if load_new_variant_data:
            genome_version = Family.objects.filter(id__in=all_family_ids).values_list('project__genome_version', flat=True).first()
            new_variant_data = _search_new_saved_variants(new_variant_keys, genome_version)
        else:
            new_variant_data = {k: v for k, v in family_variant_data.items() if k in new_variant_keys}
            new_variant_data = _get_clickhouse_variant_annotations(
                new_variant_data, primary_id_field, project=project, dataset_type=dataset_type, **kwargs,
            )

        new_variant_models = []
        for (family_id, variant_id), variant in new_variant_data.items():
            variant_json = parse_saved_variant_json(variant, family_id, variant_id=variant_id, dataset_type=dataset_type)
            if not variant.get('key'):
                variant_json['saved_variant_json'] = variant
            new_variant_models.append(SavedVariant(**variant_json))

        saved_variant_map.update({
            (v.family_id, getattr(v, primary_id_field)): v for v in SavedVariant.bulk_create(user, new_variant_models)
        })

    tag_type = VariantTagType.objects.get(name=tag_name, project=project)
    existing_tags = {
        tuple(sorted(t.saved_variant_ids)): t for t in VariantTag.objects.filter(
            variant_tag_type=tag_type, saved_variants__in=saved_variant_map.values(),
        ).annotate(saved_variant_ids=ArrayAgg('saved_variants__id', ordering='id'))
    }

    update_tags = []
    update_tag_keys = set()
    new_tag_keys = {}
    skipped_tag_keys = set()
    for key, variant in sorted(family_variant_data.items()):
        metadata = get_metadata(variant)
        comp_het_metadata = get_comp_het_metadata(variant) if get_comp_het_metadata else None
        updated_tag = _set_updated_tags(
            key, metadata, comp_het_metadata, variant.get('support_vars', []), saved_variant_map, existing_tags, tag_type, user,
            new_tag_keys, remove_missing_metadata, primary_id_field,
        )
        if updated_tag:
            update_tags.append(updated_tag)
            update_tag_keys.add(key)
        elif key not in new_tag_keys:
            skipped_tag_keys.add(key)

    VariantTag.bulk_update_models(user, update_tags, ['metadata'])

    deduped_new_tags = set()
    for key, support_key in new_tag_keys.items():
        is_dup = new_tag_keys.get(support_key) and support_key in deduped_new_tags
        if not is_dup:
            deduped_new_tags.add(key)

    return deduped_new_tags, update_tag_keys, skipped_tag_keys


def _set_updated_tags(key: tuple[int, str], metadata: dict[str, dict], comp_het_metadata: dict[str, dict], support_var_ids: list[str],
                      saved_variant_map: dict[tuple[int, str], SavedVariant], existing_tags: dict[tuple[int, ...], VariantTag],
                      tag_type: VariantTagType, user: User, new_tag_keys: dict[tuple, tuple], remove_missing_metadata: bool, primary_id_field: str):
    variant = saved_variant_map[key]
    existing_tag = existing_tags.get(tuple([variant.id]))
    updated_tag = None
    if metadata is not None and existing_tag:
        existing_metadata = json.loads(existing_tag.metadata or '{}')
        metadata = {k: existing_metadata.get(k, v) for k, v in metadata.items()}
        removed = {k: v for k, v in existing_metadata.get('removed', {}).items() if k not in metadata}
        removed.update({k: v for k, v in existing_metadata.items() if k not in metadata})
        if remove_missing_metadata and removed:
            metadata['removed'] = removed
            new_metadata = json.dumps(metadata)
            if new_metadata != existing_tag.metadata:
                existing_tag.metadata = new_metadata
                updated_tag = existing_tag
    elif metadata is not None:
        tag = create_model_from_json(
            VariantTag, {'variant_tag_type': tag_type, 'metadata': json.dumps(metadata)}, user)
        tag.saved_variants.add(variant)
        new_tag_keys[key] = None

    variant_genes = set(variant.gene_ids or [])
    support_vars = []
    for support_id in support_var_ids:
        support_v = saved_variant_map[(key[0], support_id)]
        if variant_genes.intersection(set(support_v.gene_ids)):
            support_vars.append(support_v)
    for support_var in support_vars:
        variants = [variant, support_var]
        variant_id_key = tuple(sorted([v.id for v in variants]))
        if variant_id_key not in existing_tags:
            tag = create_model_from_json(VariantTag, {
                'variant_tag_type': tag_type,
                'metadata': json.dumps(comp_het_metadata) if comp_het_metadata else None,
            }, user)
            tag.saved_variants.set(variants)
            existing_tags[variant_id_key] = True
            support_key = (key[0], getattr(support_var, primary_id_field))
            new_tag_keys[support_key] = new_tag_keys.get(support_key, key)
            new_tag_keys[key] = new_tag_keys.get(key, support_key)

    return updated_tag


def _search_new_saved_variants(family_variant_ids: set[tuple[int, str]], genome_version: str) -> dict[tuple[int, str], dict]:
    family_ids = set()
    variant_families = defaultdict(list)
    for family_id, variant_id in family_variant_ids:
        family_ids.add(family_id)
        variant_families[variant_id].append(family_id)
    families_by_id = {f.id: f for f in Family.objects.filter(id__in=family_ids)}

    samples = Sample.objects.filter(is_active=True, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
    search_variants_by_id = {
        v['variantId']: v for v in  _get_clickhouse_variants(samples, families_by_id, family_variant_ids, genome_version)
    }

    new_variants = {}
    missing = defaultdict(list)
    for variant_id, family_ids in variant_families.items():
        variant = search_variants_by_id.get(variant_id) or {'familyGuids': []}
        for family_id in family_ids:
            family = families_by_id[family_id]
            if family.guid in variant['familyGuids']:
                new_variants[(family_id, variant_id)] = variant
            else:
                missing[family.family_id].append(variant_id)

    if missing:
        missing_summary = [f'{family} ({", ".join(sorted(variant_ids))})' for family, variant_ids in missing.items()]
        raise ErrorsWarningsException([
            f"Unable to find the following family's variants in the search backend: {', '.join(missing_summary)}",
        ])

    return new_variants


def _get_clickhouse_variants(samples: Sample.objects, families_by_id: dict[int, Family], family_variant_ids: set[tuple[int, str]], genome_version: str) -> list[dict]:
    variant_data = _get_clickhouse_variant_annotations(
        {variant_id: {'genotypes': {}, 'familyGuids': []} for  variant_id in family_variant_ids}, genome_version=genome_version,
    )
    variants_by_key = {variant['key']: variant for variant in variant_data.values() if variant.get('key')}

    families = list(families_by_id.values())
    prefetch_related_objects(families, 'project')
    families_by_project = defaultdict(list)
    for family in families:
        families_by_project[family.project.guid].append(family.guid)
    for project_guid, family_guids in families_by_project.items():
        genotype_keys = get_clickhouse_genotypes(
            project_guid, family_guids, genome_version, Sample.DATASET_TYPE_VARIANT_CALLS, variants_by_key.keys(),
            samples,
        )
        for key, genotypes in genotype_keys.items():
            variants_by_key[key]['genotypes'].update(genotypes)
            variants_by_key[key]['familyGuids'] += sorted({g['familyGuid'] for g in genotypes.values()})

    return list(variants_by_key.values())


def _get_clickhouse_variant_annotations(variant_data: dict[tuple[int, str], dict], primary_id_field: str = 'variant_id', genome_version: str = None, project: Project = None, dataset_type: str = None) -> dict[tuple[int, str], dict]:
    dataset_type = dataset_type or Sample.DATASET_TYPE_VARIANT_CALLS
    variant_ids = {
        variant_id for (_, variant_id), variant in variant_data.items()
        if not (variant.get('key') and variant.get('variantId'))
    }
    keys = None
    if primary_id_field == 'key':
        keys = variant_ids
        variant_ids = None
    qs = get_variants_queryset(
        genome_version or project.genome_version, dataset_type, keys=keys, variant_ids=variant_ids,
    )
    key_field = 'variantId' if primary_id_field == 'variant_id' else primary_id_field
    variant_fields = ['key']
    variant_values = {
        'variantId': F('variant_id'),
        'gene_ids': ArrayDistinct(
            ArrayMap(qs.TRANSCRIPT_FIELD, mapped_expression='x.geneId'),
            output_field=ArrayField(StringField()),
        ),
    }
    if dataset_type.startswith('SV'):
        variant_fields += ['chrom', 'pos', 'end']
    else:
        variant_values.update(qs.split_variant_id_annotations())
    variants_by_id = {v[key_field]: v for v in qs.join_variant_id().values(*variant_fields, **variant_values)}
    for (_, variant_id), variant in variant_data.items():
        if variant_id in variants_by_id:
            variant.update(variants_by_id[variant_id])
    return variant_data


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
        keys_to_delete += redis_client.keys(pattern='variant_lookup_results__*')
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


def _requires_transcript_metadata(variant):
    if isinstance(variant, list):
        return _requires_transcript_metadata(variant[0])
    return variant.get('genomeVersion') != GENOME_VERSION_GRCh38 or variant.get('chrom', '').startswith('M')


def _get_variants_reference_data_response(variants, genome_versions, get_family_genes=False):
    response = {}
    if get_family_genes:
        response['family_genes'] = defaultdict(set)
    gene_ids = set()
    transcript_ids = set()
    for variant in variants:
        if not isinstance(variant, list):
            variant = [variant]
        for var in variant:
            for gene_id, transcripts in var.get('transcripts', {}).items():
                gene_ids.add(gene_id)
                if _requires_transcript_metadata(variant):
                    transcript_ids.update([t['transcriptId'] for t in transcripts if t.get('transcriptId')])
            if get_family_genes:
                for family_guid in var.get('familyGuids', []):
                    response['family_genes'][family_guid].update(var.get('transcripts', {}).keys())

    genome_version = list(genome_versions)[0] if len(genome_versions) == 1 else None
    genes = get_genes_for_variants(gene_ids, genome_version=genome_version)
    for gene in genes.values():
        if gene:
            gene['locusListGuids'] = []
    response['genesById'] = genes

    transcripts = {
        t['transcriptId']: t for t in get_json_for_queryset(
            TranscriptInfo.objects.filter(transcript_id__in=transcript_ids),
            nested_fields=[{'fields': ('refseqtranscript', 'refseq_id'), 'key': 'refseqId'}]
        )
    } if transcript_ids else None
    if transcripts:
        response['transcriptsById'] = transcripts

    if any(genome_version == OMIM_GENOME_VERSION for genome_version in genome_versions):
        response['omimIntervals'] = _get_omim_intervals(variants)

    _add_sample_count_stats(response, genome_versions)

    return response


def get_omim_intervals_query(variants):
    chroms = {v['chrom'] for v in variants if v.get('svType') or v.get('hasSvType')}
    return Q(phenotype_mim_number__isnull=False, gene__isnull=True, chrom__in=chroms)


def _get_omim_intervals(variants):
    omims = Omim.objects.filter(get_omim_intervals_query(variants))
    return {o.pop('id'): o for o in get_json_for_queryset(omims, additional_model_fields=['id'])}


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
    family_tpms = {}
    for agg in tpm_family_genes.iterator():
        family_guid = sample_family_map[agg['sample_id']]
        genes = {gene for gene in agg['genes'] if gene in family_genes[family_guid]}
        if family_guid in family_tpms:
            genes.update(family_tpms[family_guid]['tpmGenes'])
        if genes:
            family_tpms[family_guid] = {'tpmGenes': list(genes)}
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
                          add_locus_list_detail=False, include_individual_gene_scores=True, include_project_name=False, genome_version=None):
    response = get_json_for_saved_variants_with_tags(saved_variants, add_details=True, genome_version=genome_version) \
        if saved_variants is not None else {'savedVariantsByGuid': {}}

    variants = list(response['savedVariantsByGuid'].values()) if response_variants is None else response_variants
    if not variants:
        return response

    family_guids = {family_guid for variant in variants for family_guid in variant.get('familyGuids', [])}
    projects = Project.objects.filter(family__guid__in=family_guids).distinct()
    project = list(projects)[0] if len(projects) == 1 else None

    response.update(_get_variants_reference_data_response(
        variants, genome_versions={genome_version} if genome_version else {p.genome_version for p in projects}, get_family_genes=include_individual_gene_scores,
    ))

    discovery_tags = None
    is_analyst = user_is_analyst(request.user)
    if is_analyst:
        discovery_tags, discovery_response = get_json_for_discovery_tags(response['savedVariantsByGuid'].values(), request.user)
        response.update(discovery_response)

    response['locusListsByGuid'] = _add_locus_lists(
        projects, response['genesById'], add_list_detail=add_locus_list_detail, user=request.user)

    if discovery_tags:
        _add_discovery_tags(variants, discovery_tags)

    response['mmeSubmissionsByGuid'] = _mme_response_context(response['savedVariantsByGuid'])

    rna_tpm = _set_response_gene_scores(response, response.pop('family_genes'), response['genesById'].keys()) if include_individual_gene_scores else None

    if add_all_context or request.GET.get(LOAD_PROJECT_TAG_TYPES_CONTEXT_PARAM) == 'true':
        project_fields = {'projectGuid': 'guid'}
        if include_project_name:
            project_fields['name'] = 'name'
        if include_igv:
            project_fields['genomeVersion'] = 'genome_version'
        response['projectsByGuid'] = {project.guid: {k: getattr(project, field) for k, field in project_fields.items()} for project in projects}
        add_project_tag_types(response['projectsByGuid'])

    if add_all_context or request.GET.get(LOAD_FAMILY_CONTEXT_PARAM) == 'true':
        families = Family.objects.filter(guid__in=family_guids)
        add_families_context(
            response, families, project_guid=project.guid if project else None, user=request.user, is_analyst=is_analyst,
            has_case_review_perm=bool(project) and has_case_review_permissions(project, request.user), include_igv=include_igv,
        )

    if rna_tpm:
        if 'familiesByGuid' not in response:
            response['familiesByGuid'] = {}
        for family_guid, data in rna_tpm.items():
            if family_guid not in response['familiesByGuid']:
                response['familiesByGuid'][family_guid] = {}
            response['familiesByGuid'][family_guid].update(data)

    return response

def _mme_response_context(saved_variants_by_guid):
    mme_submission_genes = MatchmakerSubmissionGenes.objects.filter(
        saved_variant__guid__in=saved_variants_by_guid.keys()).values(
        geneId=F('gene_id'), variantGuid=F('saved_variant__guid'), submissionGuid=F('matchmaker_submission__guid'))
    for s in mme_submission_genes:
        response_variant = saved_variants_by_guid[s['variantGuid']]
        if 'mmeSubmissions' not in response_variant:
            response_variant['mmeSubmissions'] = []
        response_variant['mmeSubmissions'].append(s)

    submissions = get_json_for_matchmaker_submissions(MatchmakerSubmission.objects.filter(
        matchmakersubmissiongenes__saved_variant__guid__in=saved_variants_by_guid.keys()))
    return {s['submissionGuid']: s for s in submissions}

def _set_response_gene_scores(response, family_genes, gene_ids):
    present_family_genes = {k: v for k, v in family_genes.items() if v}
    rna_sample_family_map = dict(RnaSample.objects.filter(
        individual__family__guid__in=present_family_genes.keys(), is_active=True,
    ).values_list('id', 'individual__family__guid'))
    response['rnaSeqData'] = _get_rna_seq_outliers(gene_ids, rna_sample_family_map.keys())
    response['phenotypeGeneScores'] = get_phenotype_prioritization(present_family_genes.keys(), gene_ids=gene_ids)
    return _get_family_has_rna_tpm(present_family_genes, gene_ids, rna_sample_family_map)


def _add_sample_count_stats(response, genome_versions):
    sample_counts = Sample.objects.filter(
        is_active=True, individual__family__project__is_demo=False, individual__family__project__genome_version__in=genome_versions,
    ).values('sample_type', 'dataset_type').annotate(count=Count('*'))
    counts_by_dataset_type = defaultdict(dict)
    for sample_type, dataset_type, count in sample_counts.values_list('sample_type', 'dataset_type', 'count'):
        counts_by_dataset_type[dataset_type][sample_type] = count
    response['totalSampleCounts'] = counts_by_dataset_type
