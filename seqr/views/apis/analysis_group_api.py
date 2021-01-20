import json
import logging
from django.contrib.auth.decorators import login_required

from seqr.models import AnalysisGroup, Family
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_analysis_group
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {'name': 'Name', 'familyGuids': 'Families'}


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    missing_fields = [field for field in REQUIRED_FIELDS.keys() if not request_json.get(field)]
    if missing_fields:
        return create_json_response(
            {}, status=400, reason='Missing required field(s): {missing_field_names}'.format(
                missing_field_names=', '.join([REQUIRED_FIELDS[field] for field in missing_fields])
            ))

    families = Family.objects.filter(guid__in=request_json['familyGuids']).only('guid')
    if len(families) != len(request_json['familyGuids']):
        return create_json_response(
            {}, status=400, reason='The following families do not exist: {missing_families}'.format(
                missing_families=', '.join(set(request_json['familyGuids']) - set([family.guid for family in families]))
            ))

    if analysis_group_guid:
        analysis_group = AnalysisGroup.objects.get(guid=analysis_group_guid, project=project)
        update_model_from_json(analysis_group, request_json, user=request.user, allow_unknown_keys=True)
    else:
        analysis_group, created = get_or_create_model_from_json(AnalysisGroup, {
            'project': project,
            'name': request_json['name'],
            'description': request_json.get('description'),
            'created_by': request.user,
        }, update_json=None, user=request.user)
        if not created:
            return create_json_response(
                {}, status=400, reason='An analysis group named "{name}" already exists for project "{project}"'.format(
                    name=request_json['name'], project=project.name
                ))

    analysis_group.families.set(families)

    return create_json_response({
        'analysisGroupsByGuid': {
            analysis_group.guid: get_json_for_analysis_group(analysis_group, project_guid=project_guid)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def delete_analysis_group_handler(request, project_guid, analysis_group_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    AnalysisGroup.objects.get(guid=analysis_group_guid, project=project).delete_model(request.user, user_can_delete=True)

    return create_json_response({'analysisGroupsByGuid': {analysis_group_guid: None}})
