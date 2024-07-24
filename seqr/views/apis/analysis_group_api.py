import json

from seqr.models import AnalysisGroup, DynamicAnalysisGroup, Family
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_analysis_group
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, login_and_policies_required


REQUIRED_FIELDS = {'name': 'Name', 'familyGuids': 'Families'}


def _update_analysis_group(request, project_guid, analysis_group_guid, model_cls, required_fields, is_dynamic=False,
                           validate_body=lambda x: None, post_process_model=lambda x: None):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    missing_fields = [field for field in required_fields.keys() if not request_json.get(field)]
    if missing_fields:
        return create_json_response(
            {}, status=400, reason='Missing required field(s): {missing_field_names}'.format(
                missing_field_names=', '.join([required_fields[field] for field in missing_fields])
            ))

    error = validate_body(request_json)
    if error:
        return create_json_response({}, status=400, reason=error)

    if analysis_group_guid:
        analysis_group = model_cls.objects.get(guid=analysis_group_guid, project=project)
        update_model_from_json(analysis_group, request_json, user=request.user, allow_unknown_keys=True)
    else:
        analysis_group, created = get_or_create_model_from_json(model_cls, {
            'project': project,
            'created_by': request.user,
            **request_json,
        }, update_json=None, user=request.user)
        if not created:
            return create_json_response(
                {}, status=400, reason='An analysis group named "{name}" already exists for project "{project}"'.format(
                    name=request_json['name'], project=project.name
                ))

    post_process_model(analysis_group)

    return create_json_response({
        'analysisGroupsByGuid': {
            analysis_group.guid: get_json_for_analysis_group(analysis_group, project_guid=project_guid, is_dynamic=is_dynamic)
        },
    })


@login_and_policies_required
def update_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    valid_families = set()

    def _validate_families(request_json):
        request_json.pop('uploadedFamilyIds', None)
        family_guids = request_json.pop('familyGuids')
        families = Family.objects.filter(guid__in=family_guids).only('guid')
        if len(families) != len(family_guids):
            return 'The following families do not exist: {missing_families}'.format(
                    missing_families=', '.join(set(family_guids) - set([family.guid for family in families])))
        valid_families.update(families)

    return _update_analysis_group(
        request, project_guid, analysis_group_guid, AnalysisGroup, REQUIRED_FIELDS, validate_body=_validate_families,
        post_process_model=lambda analysis_group: analysis_group.families.set(valid_families),
    )


@login_and_policies_required
def update_dynamic_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    return _update_analysis_group(
        request, project_guid, analysis_group_guid, DynamicAnalysisGroup, is_dynamic=True,
        required_fields={f: f.title() for f in ['name', 'criteria']},
    )


@login_and_policies_required
def delete_analysis_group_handler(request, project_guid, analysis_group_guid, model_cls=AnalysisGroup):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    model_cls.objects.get(guid=analysis_group_guid, project=project).delete_model(request.user, user_can_delete=True)

    return create_json_response({'analysisGroupsByGuid': {analysis_group_guid: None}})


@login_and_policies_required
def delete_dynamic_analysis_group_handler(request, project_guid, analysis_group_guid):
    return delete_analysis_group_handler(request, project_guid, analysis_group_guid, model_cls=DynamicAnalysisGroup)
