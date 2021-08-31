import json

from seqr.views.utils.json_to_orm_utils import update_model_from_json, create_model_from_json
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.permissions_utils import check_user_created_object_permissions

def create_note_handler(request, model_cls, parent_fields, get_response_json, additional_note_fields=None):
    request_json = json.loads(request.body)

    note_fields = ['note']
    if additional_note_fields:
        note_fields += additional_note_fields
    missing_fields = [field for field in note_fields if not request_json.get(field)]
    if missing_fields:
        error = 'Missing required field(s): {}'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    create_json = {_to_snake_case(k): request_json[k] for k in note_fields}
    create_json.update(parent_fields)
    note = create_model_from_json(model_cls, create_json, request.user)

    return create_json_response(get_response_json(note))


def update_note_handler(request, model_cls, parent_id, note_guid, parent_field, get_response_json):
    note = model_cls.objects.get(guid=note_guid, **{parent_field: parent_id})
    check_user_created_object_permissions(note, request.user)

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, user=request.user, allow_unknown_keys=True)

    return create_json_response(get_response_json(note))


def delete_note_handler(request, model_cls, parent_id, note_guid, parent_field, get_response_json):
    note = model_cls.objects.get(guid=note_guid, **{parent_field: parent_id})
    note.delete_model(request.user)
    return create_json_response(get_response_json())
