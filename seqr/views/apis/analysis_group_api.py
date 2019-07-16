import json
import logging
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt

from seqr.models import AnalysisGroup, Family, CAN_EDIT
from seqr.model_utils import create_seqr_model, delete_seqr_model, update_xbrowse_family_group_families
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_analysis_group
from seqr.views.utils.permissions_utils import get_project_and_check_permissions


logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {'name': 'Name', 'familyGuids': 'Families'}


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_analysis_group_handler(request, project_guid, analysis_group_guid=None):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)

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
        update_model_from_json(analysis_group, request_json, allow_unknown_keys=True)
    else:
        try:
            analysis_group = create_seqr_model(
                AnalysisGroup,
                project=project,
                name=request_json['name'],
                description=request_json.get('description'),
                created_by=request.user,
            )
        except IntegrityError:
            return create_json_response(
                {}, status=400, reason='An analysis group named "{name}" already exists for project "{project}"'.format(
                    name=request_json['name'], project=project.name
                ))

    analysis_group.families.set(families)
    update_xbrowse_family_group_families(analysis_group, families)

    return create_json_response({
        'analysisGroupsByGuid': {
            analysis_group.guid: get_json_for_analysis_group(analysis_group, project_guid=project_guid)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_analysis_group_handler(request, project_guid, analysis_group_guid):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    analysis_group = AnalysisGroup.objects.get(guid=analysis_group_guid, project=project)

    delete_seqr_model(analysis_group)
    return create_json_response({'analysisGroupsByGuid': {analysis_group_guid: None}})
