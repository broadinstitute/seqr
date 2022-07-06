from collections import defaultdict
from django.db.models import Q, prefetch_related_objects

from seqr.models import Individual, Sample, IgvSample, AnalysisGroup, LocusList, VariantTagType,\
    VariantFunctionalData, FamilyNote, SavedVariant
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.orm_to_json_utils import _get_json_for_families, _get_json_for_individuals, _get_json_for_models, \
    get_json_for_analysis_groups, get_json_for_samples, get_json_for_locus_lists, get_json_for_projects, \
    get_json_for_family_notes, get_json_for_saved_variants


def get_projects_child_entities(projects, project_guid, user, is_analyst, include_samples=True, include_locus_list_metadata=True):
    projects_by_guid = {p['projectGuid']: p for p in get_json_for_projects(projects, user, is_analyst=is_analyst)}

    if include_samples:
        sample_models = Sample.objects.filter(individual__family__project__in=projects)
        samples = get_json_for_samples(sample_models, project_guid=project_guid, skip_nested=True, is_analyst=is_analyst)

    locus_lists_models = LocusList.objects.filter(projects__in=projects).order_by('name')
    locus_lists = get_json_for_locus_lists(locus_lists_models, user, is_analyst=is_analyst, include_metadata=include_locus_list_metadata)

    response = {
        'projectsByGuid': projects_by_guid,
        'locusListsByGuid': {ll['locusListGuid']: ll for ll in locus_lists},
        'analysisGroupsByGuid': get_project_analysis_groups(projects, project_guid),
    }
    if include_samples:
        response['samplesByGuid'] = {s['sampleGuid']: s for s in samples}

    if project_guid:
        response['projectsByGuid'][project_guid]['locusListGuids'] = [ll['locusListGuid']  for ll in locus_lists]
        response['projectsByGuid'][project_guid]['analysisGroupsLoaded'] = True
    else:
        project_id_to_guid = {project.id: project.guid for project in projects}
        for group in response['analysisGroupsByGuid'].values():
            group['projectGuid'] = project_id_to_guid[group.pop('projectId')]

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
    analysis_groups = get_json_for_analysis_groups(
        analysis_group_models, project_guid=project_guid, skip_nested=True, is_analyst=False)
    return {ag['analysisGroupGuid']: ag for ag in analysis_groups}


def add_families_context(response, family_models, project_guid, user, is_analyst, has_case_review_perm, include_igv=True, skip_child_ids=False):
    families = _get_json_for_families(
        family_models, user, project_guid=project_guid, skip_nested=skip_child_ids,
        is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)

    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__in=family_models), is_analyst=is_analyst)

    individual_models = Individual.objects.filter(family__in=family_models)
    individuals = _get_json_for_individuals(
        individual_models, user=user, project_guid=project_guid, add_hpo_details=True, skip_nested=skip_child_ids,
        is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)

    response.update({
        'familiesByGuid': {f['familyGuid']: f for f in families},
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
        'individualsByGuid': {i['individualGuid']: i for i in individuals},
    })

    if include_igv:
        igv_sample_models = IgvSample.objects.filter(individual__in=individual_models)
        igv_samples = get_json_for_samples(igv_sample_models, project_guid=project_guid, skip_nested=skip_child_ids,
                                       is_analyst=is_analyst)
        response['igvSamplesByGuid'] = {s['sampleGuid']: s for s in igv_samples}

    if not skip_child_ids:
        add_child_ids(response)

    return individual_models


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


def families_discovery_tags(families):
    families_by_guid = {f['familyGuid']: dict(discoveryTags=[], **f) for f in families}

    discovery_tags = get_json_for_saved_variants(SavedVariant.objects.filter(
        family__guid__in=families_by_guid.keys(), varianttag__variant_tag_type__category='CMG Discovery Tags',
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


def add_project_tag_types(projects_by_guid):
    variant_tag_types_models = VariantTagType.objects.filter(Q(project__guid__in=projects_by_guid.keys()) | Q(project__isnull=True))
    variant_tag_types = _get_json_for_models(variant_tag_types_models)

    project_tag_types = defaultdict(list)
    if len(projects_by_guid) == 1:
        project_guid = next(iter((projects_by_guid.keys())))
        project_tag_types[project_guid] = variant_tag_types
    else:
        prefetch_related_objects(variant_tag_types_models, 'project')
        variant_tag_types_by_guid = {vtt['variantTagTypeGuid']: vtt for vtt in variant_tag_types}
        for vtt in variant_tag_types_models:
            project_guid = vtt.project.guid if vtt.project else None
            project_tag_types[project_guid].append(variant_tag_types_by_guid[vtt.guid])

    for project_guid, project_json in projects_by_guid.items():
        project_json.update({
            'variantTagTypes': sorted(
                project_tag_types[project_guid] + project_tag_types[None],
                key=lambda variant_tag_type: variant_tag_type['order'] or 0,
            ),
            'variantFunctionalTagTypes': VariantFunctionalData.FUNCTIONAL_DATA_TAG_TYPES,
        })
