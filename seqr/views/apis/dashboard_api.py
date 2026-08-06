from django.db import models
from django.db.models.functions import Coalesce

from seqr.models import ProjectCategory, Individual, RnaSample, Family, AnalysisGroup, Project
from seqr.views.utils.individual_utils import check_project_individuals_deletable
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_projects, get_json_for_analysis_groups
from seqr.views.utils.permissions_utils import get_project_analysis_group_guids_user_can_view, login_and_policies_required


@login_and_policies_required
def dashboard_page_data(request):
    project_guids, analysis_group_guids = get_project_analysis_group_guids_user_can_view(request.user, limit_data_manager=False)

    projects_by_guid = _get_projects_json(project_guids, request.user)
    analysis_groups_by_guid = _get_analysis_groups_json(analysis_group_guids)
    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid.keys())

    json_response = {
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
        'analysisGroupsByGuid': analysis_groups_by_guid,
    }

    return create_json_response(json_response)


def _get_projects_json(project_guids, user):
    return _get_entities_json(project_guids, Project, 'projectGuid', get_json_for_projects, user=user)


def _get_analysis_groups_json(analysis_group_guids):
    return _get_entities_json(
        analysis_group_guids, AnalysisGroup, 'analysisGroupGuid', get_json_for_analysis_groups,
        family_field='families', is_dynamic=True, additional_model_fields=['created_date'],
    )


def _get_entities_json(guids, model_cls, guid_field, get_json_func, family_field='family', **kwargs):
    if not guids:
        return {}

    models_with_counts = model_cls.objects.filter(guid__in=guids).annotate(
        numFamilies=models.Count(family_field, distinct=True),
        numIndividuals=models.Count(f'{family_field}__individual', distinct=True),
        numVariantTags=models.Count(f'{family_field}__savedvariant', distinct=True),
    )

    models_by_guid = {p[guid_field]: p for p in get_json_func(models_with_counts, **kwargs)}
    for model in models_with_counts:
        models_by_guid[model.guid].update({
            field: getattr(model, field) for field in ['numFamilies', 'numIndividuals', 'numVariantTags']
        })
        if models_by_guid[model.guid].get('userIsCreator'):
            errors, _ = check_project_individuals_deletable(model)
            models_by_guid[model.guid]['userCanDelete'] = not errors

    cls_name = model_cls.__name__.lower()
    analysis_status_counts = Family.objects.filter(**{f'{cls_name}__in': models_with_counts}).values(
        f'{cls_name}__guid', 'analysis_status').annotate(count=models.Count('*'))
    for agg in analysis_status_counts:
        guid = agg[f'{cls_name}__guid']
        if 'analysisStatusCounts' not in models_by_guid[guid]:
            models_by_guid[guid]['analysisStatusCounts'] = {}
        models_by_guid[guid]['analysisStatusCounts'][agg['analysis_status']] = agg['count']

    sample_type_status_counts = list(
        Individual.objects.filter(**{f'family__{cls_name}__in': models_with_counts}).annotate(sample_type=Coalesce(
            models.F('active_datasets__sample_type'), models.F('inactive_datasets__sample_type'),
        )).filter(sample_type__isnull=False).values('sample_type', model_guid=models.F(f'family__{cls_name}__guid')).annotate(
            count=models.Count('id', distinct=True)
        )
    ) + list(
        RnaSample.objects.filter(**{f'individual__family__{cls_name}__in': models_with_counts}).values(
            model_guid=models.F(f'individual__family__{cls_name}__guid')
        ).annotate(sample_type=models.Value('RNA'), count=models.Count('individual_id', distinct=True))
    )
    for agg in sample_type_status_counts:
        guid = agg['model_guid']
        if 'sampleTypeCounts' not in models_by_guid[guid]:
            models_by_guid[guid]['sampleTypeCounts'] = {}
        models_by_guid[guid]['sampleTypeCounts'][agg['sample_type']] = agg['count']

    return models_by_guid


def _retrieve_project_categories_by_guid(project_guids):
    if len(project_guids) == 0:
        return {}

    # retrieve all project categories
    project_categories = ProjectCategory.objects.filter(projects__guid__in=project_guids).distinct()

    project_categories_by_guid = {}
    for project_category in project_categories:
        project_categories_by_guid[project_category.guid] = project_category.json()

    return project_categories_by_guid
