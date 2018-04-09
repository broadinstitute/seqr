import logging

logger = logging.getLogger(__name__)

PROJECT_JSON_FIELD_MAP = dict([
    ('name',                    'name'),
    ('description',             'description'),
    ('deprecatedProjectId',     'deprecated_project_id'),
])

FAMILY_JSON_FIELD_MAP = dict([
    ('familyId',   'family_id'),
    ('displayName', 'display_name'),
    ('description', 'description'),
    ('analysisNotes', 'analysis_notes'),
    ('analysisSummary', 'analysis_summary'),
    ('causalInheritanceMode', 'causal_inheritance_mode'),
    ('analysisStatus', 'analysis_status'),

    #('internal_analysis_status', 'internal_analysis_status'),
    #('internal_case_review_notes', 'internal_case_review_notes'),
    #('internal_case_review_summary', 'internal_case_review_summary'),
])

INDIVIDUAL_JSON_FIELD_MAP = dict([
    ('individualId',           'individual_id'),
    ('paternalId',             'paternal_id'),
    ('maternalId',             'maternal_id'),
    ('sex',                    'sex'),
    ('affected',               'affected'),
    ('displayName',            'display_name'),
    ('notes',                  'notes'),
    ('family',                 'family'),
])

INTERNAL_INDIVIDUAL_JSON_FIELD_MAP = dict([
    ('caseReviewStatus',       'case_review_status'),
    ('caseReviewSstatusAcceptedFor',  'case_review_status_accepted_for'),
    ('caseReviewDiscussion',   'case_review_discussion'),
])


def update_project_from_json(project, json, verbose=False):

    _update_model_from_json(project, json, PROJECT_JSON_FIELD_MAP, verbose=verbose)


def update_family_from_json(family, json, verbose=False):

    _update_model_from_json(family, json, FAMILY_JSON_FIELD_MAP, verbose=verbose)


def update_individual_from_json(individual, json, verbose=False, allow_unknown_keys=False, save=True, user=None):

    json_field_map = {}
    json_field_map.update(INDIVIDUAL_JSON_FIELD_MAP)
    if user and user.is_staff and user.is_active:
        json_field_map.update(INTERNAL_INDIVIDUAL_JSON_FIELD_MAP)

    _update_model_from_json(individual, json, json_field_map, verbose=verbose, allow_unknown_keys=allow_unknown_keys, save=save)


def _update_model_from_json(model_obj, json, json_field_map, verbose=False, allow_unknown_keys=False, save=True):
    unknown_keys = set(json.keys()) - set(json_field_map.keys())
    if unknown_keys and not allow_unknown_keys:
        raise ValueError("Unexpected keys: {0}".format(", ".join(unknown_keys)))

    modified = False
    for json_key, value in json.items():
        if json_key in unknown_keys:
            continue
        orm_key = json_field_map[json_key]
        if getattr(model_obj, orm_key) != value:
            modified = True
            if verbose:
                model_obj_name = getattr(model_obj, 'guid', model_obj.__name__)
                logger.info("Setting {0}.{1} to {2}".format(model_obj_name, orm_key, value))
            setattr(model_obj, orm_key, value)

    if modified and save:
        model_obj.save()
