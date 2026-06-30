from django.core.exceptions import PermissionDenied
import json

from seqr.models import AnalysisGroup, DynamicAnalysisGroup, Family
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_analysis_group
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, login_and_policies_required, \
    user_is_pm, is_valid_anvil_workspace


REQUIRED_FIELDS = {'name': 'Name', 'familyGuids': 'Families'}


def _update_analysis_group(request, project_guid, analysis_group_guid, model_cls, required_fields, is_dynamic=False,
                           validate_body=lambda x: None, post_process_model=lambda x: None, pm_fields=None):
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

    pm_fields = {field: request_json[field] for field in (pm_fields or {}) if request_json.get(field)}
    if analysis_group_guid:
        analysis_group = model_cls.objects.get(guid=analysis_group_guid, project=project)
        _check_pm_field_permissions(pm_fields, request.user, analysis_group)
        update_model_from_json(analysis_group, request_json, user=request.user, allow_unknown_keys=True)
    else:
        _check_pm_field_permissions(pm_fields, request.user)
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


def _check_pm_field_permissions(pm_fields, user, analysis_group=None):
    if not pm_fields:
        return
    if analysis_group and all(getattr(analysis_group, _to_snake_case(field)) == value for field, value in pm_fields.items()):
        return
    if user_is_pm(user) and is_valid_anvil_workspace(pm_fields, user):
        return
    raise PermissionDenied(f'{user} does not have permission to edit {",".join(pm_fields)}')


@login_and_policies_required
def update_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    valid_families = set()
    workspace_fields = ['workspaceName', 'workspaceNamespace']

    def _validate_body(request_json):
        request_json.pop('uploadedFamilyIds', None)
        family_guids = request_json.pop('familyGuids')
        families = Family.objects.filter(guid__in=family_guids).only('guid')
        if len(families) != len(family_guids):
            return 'The following families do not exist: {missing_families}'.format(
                    missing_families=', '.join(set(family_guids) - set([family.guid for family in families])))
        valid_families.update(families)

        edit_workspace_fields = [request_json[field] for field in workspace_fields if request_json.get(field)]
        if len(edit_workspace_fields) == 1:
            return 'Both Workspace Name and Workspace Namespace are required to add access control'
        return None

    return _update_analysis_group(
        request, project_guid, analysis_group_guid, AnalysisGroup, REQUIRED_FIELDS, validate_body=_validate_body,
        post_process_model=lambda analysis_group: analysis_group.families.set(valid_families),
        pm_fields=workspace_fields,
    )


@login_and_policies_required
def update_dynamic_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    return _update_analysis_group(
        request, project_guid, analysis_group_guid, DynamicAnalysisGroup, is_dynamic=True,
        required_fields={f: f.title() for f in ['name', 'criteria']},
    )


@login_and_policies_required
def delete_analysis_group_handler(request, project_guid, analysis_group_guid, model_cls=AnalysisGroup, check_workspace=True):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    analysis_group = model_cls.objects.get(guid=analysis_group_guid, project=project)
    if check_workspace and (analysis_group.workspace_namespace or analysis_group.workspace_name):
        return create_json_response({}, status=400, reason='Unable to delete access control group')

    analysis_group.delete_model(request.user, user_can_delete=True)

    return create_json_response({'analysisGroupsByGuid': {analysis_group_guid: None}})


@login_and_policies_required
def delete_dynamic_analysis_group_handler(request, project_guid, analysis_group_guid):
    return delete_analysis_group_handler(request, project_guid, analysis_group_guid, model_cls=DynamicAnalysisGroup, check_workspace=False)
