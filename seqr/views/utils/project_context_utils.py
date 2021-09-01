from collections import defaultdict
from django.db.models import Q, prefetch_related_objects

from seqr.models import Family, Individual, Sample, IgvSample, AnalysisGroup, LocusList, VariantTagType
from seqr.views.utils.orm_to_json_utils import _get_json_for_families, _get_json_for_individuals, \
    get_json_for_analysis_groups, get_json_for_samples, get_json_for_locus_lists, get_json_for_projects, \
    get_json_for_variant_functional_data_tag_types, _get_json_for_models
from seqr.views.utils.permissions_utils import has_case_review_permissions, user_is_analyst


def get_projects_child_entities(projects, user, is_analyst=None):
    project_guid = projects[0].guid if len(projects) == 1 else None
    has_case_review_perm = has_case_review_permissions(projects[0], user)
    if is_analyst is None:
        is_analyst = user_is_analyst(user)

    projects_by_guid = {p['projectGuid']: p for p in get_json_for_projects(projects, user)}

    family_models = Family.objects.filter(project__in=projects)
    families = _get_json_for_families(
        family_models, user, project_guid=project_guid, skip_nested=True,
        is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)

    individual_models = Individual.objects.filter(family__in=family_models)
    individuals = _get_json_for_individuals(
        individual_models, user=user, project_guid=project_guid, add_hpo_details=True, skip_nested=True,
        is_analyst=is_analyst, has_case_review_perm=has_case_review_perm)

    sample_models = Sample.objects.filter(individual__in=individual_models)
    samples = get_json_for_samples(sample_models, project_guid=project_guid, skip_nested=True)

    igv_sample_models = IgvSample.objects.filter(individual__in=individual_models)
    igv_samples = get_json_for_samples(igv_sample_models, project_guid=project_guid, skip_nested=True)

    analysis_group_models = AnalysisGroup.objects.filter(project__in=projects)
    analysis_groups = get_json_for_analysis_groups(analysis_group_models, project_guid=project_guid, skip_nested=True)

    locus_lists_models = LocusList.objects.filter(projects__in=projects)
    locus_lists_by_guid = {
        ll['locusListGuid']: ll for ll in get_json_for_locus_lists(locus_lists_models, user, is_analyst=is_analyst)}

    functional_data_tag_types = get_json_for_variant_functional_data_tag_types()

    variant_tag_types_models = VariantTagType.objects.filter(Q(project__in=projects) | Q(project__isnull=True))
    variant_tag_types = _get_json_for_models(variant_tag_types_models)

    project_locus_lists = defaultdict(list)
    project_tag_types = defaultdict(list)
    if project_guid:
        project_locus_lists[project_guid] = list(locus_lists_by_guid.keys())
        project_tag_types[project_guid] = variant_tag_types
    else:
        project_id_to_guid = {project.id: project.guid for project in projects}
        family_id_to_guid = {family.id: family.guid for family in family_models}
        individual_id_to_guid = {individual.id: individual.guid for individual in individual_models}
        family_guid_to_project_guid = {}
        individual_guid_to_project_guid = {}
        for family in families:
            project_guid = project_id_to_guid[family.pop('projectId')]
            family['projectGuid'] = project_guid
            family_guid_to_project_guid[family['familyGuid']] = project_guid
        for individual in individuals:
            family_guid = family_id_to_guid[individual.pop('familyId')]
            project_guid = family_guid_to_project_guid[family_guid]
            individual['familyGuid'] = family_guid
            individual['projectGuid'] = project_guid
            individual_guid_to_project_guid[individual['individualGuid']] = project_guid
        for sample in samples:
            individual_guid = individual_id_to_guid[sample.pop('individualId')]
            sample['individualGuid'] = individual_guid
            sample['projectGuid'] = individual_guid_to_project_guid[individual_guid]
        for sample in igv_samples:
            individual_guid = individual_id_to_guid[sample.pop('individualId')]
            sample['individualGuid'] = individual_guid
            sample['projectGuid'] = individual_guid_to_project_guid[individual_guid]
        for group in analysis_groups:
            group['projectGuid'] = project_id_to_guid[group.pop('projectId')]

        prefetch_related_objects(locus_lists_models, 'projects')
        for locus_list in locus_lists_models:
            for project in locus_list.projects.all():
                project_locus_lists[project.guid].append(locus_list.guid)

        prefetch_related_objects(variant_tag_types_models, 'project')
        variant_tag_types_by_guid = {vtt['variantTagTypeGuid']: vtt for vtt in variant_tag_types}
        for vtt in variant_tag_types_models:
            project_guid = vtt.project.guid if vtt.project else None
            project_tag_types[project_guid].append(variant_tag_types_by_guid[vtt.guid])

    for project_guid, project_json in projects_by_guid.items():
        project_json.update({
            'locusListGuids': project_locus_lists[project_guid],
            'variantTagTypes': project_tag_types[project_guid] + project_tag_types[None],
            'variantFunctionalTagTypes': functional_data_tag_types,
        })

    individual_guids_by_family = defaultdict(list)
    for individual in individuals:
        individual_guids_by_family[individual['familyGuid']].append(individual['individualGuid'])
    for family in families:
         family['individualGuids'] = individual_guids_by_family[family['familyGuid']]

    sample_guids_by_individual = defaultdict(list)
    for sample in samples:
        sample_guids_by_individual[sample['individualGuid']].append(sample['sampleGuid'])
    igv_sample_guids_by_individual = defaultdict(list)
    for sample in igv_samples:
        igv_sample_guids_by_individual[sample['individualGuid']].append(sample['sampleGuid'])
    for individual in individuals:
        individual['sampleGuids'] = sample_guids_by_individual[individual['individualGuid']]
        individual['igvSampleGuids'] = igv_sample_guids_by_individual[individual['individualGuid']]

    response = {
        'projectsByGuid': projects_by_guid,
        'familiesByGuid': {f['familyGuid']: f for f in families},
        'individualsByGuid': {i['individualGuid']: i for i in individuals},
        'samplesByGuid': {s['sampleGuid']: s for s in samples},
        'igvSamplesByGuid': {s['sampleGuid']: s for s in igv_samples},
        'locusListsByGuid': locus_lists_by_guid,
        'analysisGroupsByGuid': {ag['analysisGroupGuid']: ag for ag in analysis_groups},
    }

    return response
