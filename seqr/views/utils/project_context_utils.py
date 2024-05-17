from collections import defaultdict
from django.db.models import Count, Q, F, prefetch_related_objects

from seqr.models import Individual, IgvSample, AnalysisGroup, DynamicAnalysisGroup, LocusList, VariantTagType,\
    VariantFunctionalData, FamilyNote, SavedVariant, VariantTag, VariantNote
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.orm_to_json_utils import _get_json_for_families, _get_json_for_individuals, get_json_for_queryset, \
    get_json_for_analysis_groups, get_json_for_samples, get_json_for_locus_lists, \
    get_json_for_family_notes, get_json_for_saved_variants


def get_projects_child_entities(projects, project_guid, user):
    projects_by_guid = {p.guid: {'projectGuid': p.guid, 'name': p.name} for p in projects}

    locus_list_json, locus_lists_models = get_project_locus_lists(projects, user)

    response = {
        'projectsByGuid': projects_by_guid,
        'locusListsByGuid': locus_list_json,
        'analysisGroupsByGuid': get_project_analysis_groups(projects, project_guid),
    }

    if project_guid:
        response['projectsByGuid'][project_guid]['locusListGuids'] = list(locus_list_json.keys())
        response['projectsByGuid'][project_guid]['analysisGroupsLoaded'] = True
    else:
        project_id_to_guid = {project.id: project.guid for project in projects}
        for group in response['analysisGroupsByGuid'].values():
            group['projectGuid'] = project_id_to_guid.get(group.pop('projectId'))

        for project in response['projectsByGuid'].values():
            project['locusListGuids'] = []
            project['analysisGroupsLoaded'] = True
        prefetch_related_objects(locus_lists_models, 'projects')
        for locus_list in locus_lists_models:
            for project in locus_list.projects.all():
                if project.guid in response['projectsByGuid']:
                    response['projectsByGuid'][project.guid]['locusListGuids'].append(locus_list.guid)

    return response


def get_project_analysis_groups(projects, project_guid):
    analysis_group_models = AnalysisGroup.objects.filter(project__in=projects)
    get_json_kwargs = dict(project_guid=project_guid, skip_nested=True, is_analyst=False)
    analysis_groups = get_json_for_analysis_groups(analysis_group_models, **get_json_kwargs)
    dynamic_analysis_group_models = DynamicAnalysisGroup.objects.filter(Q(project__in=projects) | Q(project__isnull=True))
    dynamic_analysis_groups = get_json_for_analysis_groups(dynamic_analysis_group_models, **get_json_kwargs, is_dynamic=True)
    return {ag['analysisGroupGuid']: ag for ag in analysis_groups + dynamic_analysis_groups}


def get_project_locus_lists(projects, user, include_metadata=False):
    locus_lists_models = LocusList.objects.filter(projects__in=projects).order_by('name')
    locus_lists = get_json_for_locus_lists(locus_lists_models, user, include_metadata=include_metadata)
    return {ll['locusListGuid']: ll for ll in locus_lists}, locus_lists_models


def add_families_context(response, family_models, project_guid, user, is_analyst, has_case_review_perm, include_igv=True):
    families = _get_json_for_families(
        family_models, user, project_guid=project_guid, is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)

    families_by_guid = {f['familyGuid']: f for f in families}

    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__guid__in=families_by_guid.keys()), is_analyst=is_analyst)

    individual_models = Individual.objects.filter(family__guid__in=families_by_guid.keys())
    individuals = _get_json_for_individuals(
        individual_models, user=user, project_guid=project_guid, add_hpo_details=True,
        is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)
    individuals_by_guid = {i['individualGuid']: i for i in individuals}

    context = {
        'familiesByGuid': families_by_guid,
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
        'individualsByGuid': individuals_by_guid,
    }
    for k, v in context.items():
        if k not in response:
            response[k] = {}
        response[k].update(v)

    if include_igv:
        igv_sample_models = IgvSample.objects.filter(individual__guid__in=individuals_by_guid.keys())
        igv_samples = get_json_for_samples(igv_sample_models, project_guid=project_guid, is_analyst=is_analyst)
        response['igvSamplesByGuid'] = {s['sampleGuid']: s for s in igv_samples}

    add_child_ids(response)


def add_child_ids(response):
    if 'samplesByGuid' in response:
        sample_guids_by_individual = defaultdict(list)
        for sample in response['samplesByGuid'].values():
            sample_guids_by_individual[sample['individualGuid']].append(sample['sampleGuid'])

    if 'igvSamplesByGuid' in response:
        igv_sample_guids_by_individual = defaultdict(list)
        for sample in response['igvSamplesByGuid'].values():
            igv_sample_guids_by_individual[sample['individualGuid']].append(sample['sampleGuid'])

    individual_guids_by_family = defaultdict(list)
    for individual in response['individualsByGuid'].values():
        if 'samplesByGuid' in response:
            individual['sampleGuids'] = sample_guids_by_individual[individual['individualGuid']]
        if 'igvSamplesByGuid' in response:
            individual['igvSampleGuids'] = igv_sample_guids_by_individual[individual['individualGuid']]
        individual_guids_by_family[individual['familyGuid']].append(individual['individualGuid'])

    for family in response['familiesByGuid'].values():
        family['individualGuids'] = individual_guids_by_family[family['familyGuid']]


def families_discovery_tags(families, project=None):
    families_by_guid = {f['familyGuid']: dict(discoveryTags=[], **f) for f in families}

    family_filter = {'family__project': project} if project else {'family__guid__in': families_by_guid.keys()}
    discovery_tags = get_json_for_saved_variants(SavedVariant.objects.filter(
        varianttag__variant_tag_type__category='CMG Discovery Tags', **family_filter,
    ), add_details=True)

    gene_ids = set()
    for tag in discovery_tags:
        gene_ids.update(list(tag.get('transcripts', {}).keys()))
        for family_guid in tag['familyGuids']:
            families_by_guid[family_guid]['discoveryTags'].append(tag)

    return {
        'familiesByGuid': families_by_guid,
        'genesById': get_genes(gene_ids),
    }


MME_TAG_NAME = 'MME Submission'


def add_project_tag_types(projects_by_guid, project=None):
    is_single_project = len(projects_by_guid) == 1
    project_q = dict(project=project) if project else dict(project__guid__in=projects_by_guid.keys())
    variant_tag_types_models = VariantTagType.objects.filter(Q(**project_q) | Q(project__isnull=True))
    variant_tag_types = get_json_for_queryset(
        variant_tag_types_models, nested_fields=None if is_single_project else [{'fields': ('project', 'guid')}])

    project_tag_types = defaultdict(list)
    if is_single_project:
        project_guid = next(iter((projects_by_guid.keys())))
        project_tag_types[project_guid] = list(variant_tag_types)
    else:
        for vtt in variant_tag_types:
            project_tag_types[vtt.pop('projectGuid')].append(vtt)

    project_tag_types[None].append({
        'variantTagTypeGuid': 'mmeSubmissionVariants',
        'name': MME_TAG_NAME,
        'category': 'Matchmaker',
        'description': '',
        'color': '#6435c9',
        'order': 99,
    })

    for project_guid, project_json in projects_by_guid.items():
        project_json.update({
            'variantTagTypes': sorted(
                project_tag_types[project_guid] + project_tag_types[None],
                key=lambda variant_tag_type: variant_tag_type['order'] or 0,
            ),
            'variantFunctionalTagTypes': VariantFunctionalData.FUNCTIONAL_DATA_TAG_TYPES,
        })


def add_project_tag_type_counts(project, response_json, project_json=None):
    project_json = project_json or {}
    response_json['projectsByGuid'] = {project.guid: project_json}
    add_project_tag_types(response_json['projectsByGuid'], project=project)

    saved_variants = SavedVariant.objects.filter(family__project=project)
    project_tags = VariantTag.objects.filter(saved_variants__in=saved_variants)
    project_notes = VariantNote.saved_variants.through.objects.filter(savedvariant_id__in=saved_variants)

    family_tag_type_counts = defaultdict(dict)

    note_tag_type = {
        'variantTagTypeGuid': 'notes',
        'name': 'Has Notes',
        'category': 'Notes',
        'description': '',
        'color': 'grey',
        'order': 100,
        'numTags': project_notes.values_list('savedvariant_id').distinct().count(),
    }

    mme_counts_by_family = saved_variants.filter(matchmakersubmissiongenes__isnull=False) \
        .values(family_guid=F('family__guid')).annotate(count=Count('guid', distinct=True))

    tag_counts_by_type_and_family = defaultdict(list)
    for counts in project_tags.values(
        'variant_tag_type__name', family_guid=F('saved_variants__family__guid')).annotate(count=Count('guid', distinct=True)):
        tag_counts_by_type_and_family[counts['variant_tag_type__name']].append(counts)
    tag_counts_by_type_and_family[MME_TAG_NAME] = mme_counts_by_family

    project_variant_tags = project_json['variantTagTypes']
    for tag_type in project_variant_tags:
        current_tag_type_counts = tag_counts_by_type_and_family[tag_type['name']]
        num_tags = sum(count['count'] for count in current_tag_type_counts)
        tag_type.update({
            'numTags': num_tags,
        })
        for count in current_tag_type_counts:
            family_tag_type_counts[count['family_guid']].update({tag_type['name']: count['count']})

    project_variant_tags.append(note_tag_type)
    response_json['familyTagTypeCounts'] = family_tag_type_counts
