"""
APIs used to retrieve and modify Individual fields
"""
import json
from collections import defaultdict
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.fields.files import ImageFieldFile

from matchmaker.models import MatchmakerSubmission
from seqr.utils.gene_utils import get_genes_for_variant_display
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.individual_utils import delete_individuals
from seqr.views.utils.json_to_orm_utils import update_family_from_json, update_model_from_json, \
    get_or_create_model_from_json, create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.note_utils import create_note_handler, update_note_handler, delete_note_handler
from seqr.views.utils.orm_to_json_utils import _get_json_for_model,  get_json_for_family_note, get_json_for_samples, \
    get_json_for_matchmaker_submissions, get_json_for_analysis_groups, _get_json_for_families, get_json_for_queryset
from seqr.views.utils.project_context_utils import add_families_context, families_discovery_tags, add_project_tag_types, \
    MME_TAG_NAME
from seqr.models import Family, FamilyAnalysedBy, Individual, FamilyNote, Sample, VariantTag, AnalysisGroup, RnaSeqTpm, \
    PhenotypePrioritization, Project
from seqr.views.utils.permissions_utils import check_project_permissions, get_project_and_check_pm_permissions, \
    login_and_policies_required, user_is_analyst, has_case_review_permissions
from seqr.views.utils.variant_utils import get_phenotype_prioritization


FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'

@login_and_policies_required
def family_page_data(request, family_guid):
    families = Family.objects.filter(guid=family_guid)
    family = families.first()
    project = family.project
    check_project_permissions(project, request.user)
    is_analyst = user_is_analyst(request.user)
    has_case_review_perm = has_case_review_permissions(project, request.user)

    sample_models = Sample.objects.filter(individual__family=family)
    samples = get_json_for_samples(sample_models, project_guid=project.guid, family_guid=family_guid, skip_nested=True, is_analyst=is_analyst)
    response = {
        'samplesByGuid': {s['sampleGuid']: s for s in samples},
    }

    add_families_context(response, families, project.guid, request.user, is_analyst, has_case_review_perm)
    response['familiesByGuid'][family_guid]['detailsLoaded'] = True

    outlier_individual_guids = sample_models.filter(sample_type=Sample.SAMPLE_TYPE_RNA)\
        .exclude(rnaseqoutlier__isnull=True, rnaseqspliceoutlier__isnull=True).values_list('individual__guid', flat=True)
    for individual_guid in outlier_individual_guids:
        response['individualsByGuid'][individual_guid]['hasRnaOutlierData'] = True

    has_phentoype_score_indivs = PhenotypePrioritization.objects.filter(individual__family=family).values_list(
        'individual__guid', flat=True)
    for individual_guid in has_phentoype_score_indivs:
        response['individualsByGuid'][individual_guid]['hasPhenotypeGeneScores'] = True

    submissions = get_json_for_matchmaker_submissions(MatchmakerSubmission.objects.filter(individual__family=family))
    individual_mme_submission_guids = {s['individualGuid']: s['submissionGuid'] for s in submissions}
    for individual in response['individualsByGuid'].values():
        individual['mmeSubmissionGuid'] = individual_mme_submission_guids.get(individual['individualGuid'])
    response['mmeSubmissionsByGuid'] = {s['submissionGuid']: s for s in submissions}

    return create_json_response(response)

@login_and_policies_required
def family_variant_tag_summary(request, family_guid):
    family = Family.objects.get(guid=family_guid)
    project = family.project
    check_project_permissions(project, request.user)

    response = families_discovery_tags([{'familyGuid': family_guid}])

    tags = VariantTag.objects.filter(saved_variants__family=family)
    family_tag_type_counts = tags.values('variant_tag_type__name').annotate(count=Count('*'))
    response['familyTagTypeCounts'] = {
        family_guid: {c['variant_tag_type__name']: c['count'] for c in family_tag_type_counts},
    }
    response['familyTagTypeCounts'][family_guid][MME_TAG_NAME] = tags.filter(
        saved_variants__matchmakersubmissiongenes__isnull=False).values('saved_variants__guid').distinct().count()

    response['projectsByGuid'] = {project.guid: {}}
    add_project_tag_types(response['projectsByGuid'])

    return create_json_response(response)


@login_and_policies_required
def edit_families_handler(request, project_guid):
    """Edit or one or more Family records.

    Args:
        project_guid (string): GUID of project that contains these individuals.
    """

    project = get_project_and_check_pm_permissions(project_guid, request.user)

    request_json = json.loads(request.body)

    if request_json.get('uploadedFileId'):
        modified_families = load_uploaded_file(request_json.get('uploadedFileId'))
    else:
        modified_families = request_json.get('families')
    if modified_families is None:
        return create_json_response(
            {}, status=400, reason="'families' not specified")

    family_guids = [f['familyGuid'] for f in modified_families if f.get('familyGuid')]
    family_models = {}
    if family_guids:
        family_models.update({f.guid: f for f in Family.objects.filter(project=project, guid__in=family_guids)})
        if len(family_models) != len(family_guids):
            missing_guids = set(family_guids) - set(family_models.keys())
            return create_json_response({'error': 'Invalid family guids: {}'.format(', '.join(missing_guids))}, status=400)

        updated_family_ids = {
            fields[FAMILY_ID_FIELD]: family_models[fields['familyGuid']].family_id for fields in modified_families
            if fields.get('familyGuid') and fields.get(FAMILY_ID_FIELD) and \
                fields[FAMILY_ID_FIELD] != family_models[fields['familyGuid']].family_id}
        existing_families = {
            f.family_id for f in Family.objects.filter(project=project, family_id__in=updated_family_ids.keys())
        }
        if existing_families:
            return create_json_response({
                'error': 'Cannot update the following family ID(s) as they are already in use: {}'.format(', '.join([
                    '{} -> {}'.format(old_id, new_id) for new_id, old_id in updated_family_ids.items()
                    if new_id in existing_families
                ]))}, status=400)

    no_guid_families = [f for f in modified_families if not f.get('familyGuid')]
    if no_guid_families:
        prev_ids = [f[PREVIOUS_FAMILY_ID_FIELD] for f in no_guid_families if f.get(PREVIOUS_FAMILY_ID_FIELD)]
        prev_id_models = {f.family_id: f for f in Family.objects.filter(project=project, family_id__in=prev_ids)}
        if len(prev_id_models) != len(prev_ids):
            missing_ids = set(prev_ids) - set(prev_id_models.keys())
            return create_json_response(
                {'error': 'Invalid previous family ids: {}'.format(', '.join(missing_ids))}, status=400)
        family_models.update(prev_id_models)

    updated_family_ids = []
    for fields in modified_families:
        if fields.get('familyGuid'):
            family = family_models[fields['familyGuid']]
        elif fields.get(PREVIOUS_FAMILY_ID_FIELD):
            family = family_models[fields[PREVIOUS_FAMILY_ID_FIELD]]
        else:
            family, _ = get_or_create_model_from_json(
                Family, {'project': project, 'family_id': fields[FAMILY_ID_FIELD]},
                update_json=None, user=request.user)

        update_family_from_json(family, fields, user=request.user, allow_unknown_keys=True)
        updated_family_ids.append(family.id)

    updated_families_by_guid = {
        'familiesByGuid': {
            family['familyGuid']: family for family in _get_json_for_families(
                Family.objects.filter(id__in=updated_family_ids), request.user, add_individual_guids_field=True)
        }
    }

    return create_json_response(updated_families_by_guid)


@login_and_policies_required
def delete_families_handler(request, project_guid):
    """Edit or delete one or more Individual records.

    Args:
        project_guid (string): GUID of project that contains these individuals.
    """

    project = get_project_and_check_pm_permissions(project_guid, request.user)

    request_json = json.loads(request.body)

    families_to_delete = request_json.get('families')
    if families_to_delete is None:
        return create_json_response(
            {}, status=400, reason="'recordIdsToDelete' not specified")
    family_guids_to_delete = [f['familyGuid'] for f in families_to_delete]

    # delete individuals 1st
    individual_guids_to_delete = [i.guid for i in Individual.objects.filter(
        family__project=project, family__guid__in=family_guids_to_delete)]
    delete_individuals(project, individual_guids_to_delete, request.user)

    # delete families
    Family.bulk_delete(request.user, project=project, guid__in=family_guids_to_delete)

    # send response
    return create_json_response({
        'individualsByGuid': {
            individual_guid: None for individual_guid in individual_guids_to_delete
        },
        'familiesByGuid': {
            family_guid: None for family_guid in family_guids_to_delete
        },
    })


@login_and_policies_required
def update_family_fields_handler(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)

    # check permission - can be edited by anyone with access to the project
    check_project_permissions(family.project, request.user)

    request_json = json.loads(request.body)
    update_family_from_json(family, request_json, user=request.user, allow_unknown_keys=True, immutable_keys=[
        'family_id', 'display_name',
    ])

    return create_json_response({
        family.guid: _get_json_for_model(family, user=request.user)
    })


@login_and_policies_required
def update_family_assigned_analyst(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
    """
    family = Family.objects.get(guid=family_guid)
    # assigned_analyst can be edited by anyone with access to the project
    check_project_permissions(family.project, request.user, can_edit=False)

    request_json = json.loads(request.body)
    assigned_analyst_username = request_json.get('assigned_analyst_username')

    if assigned_analyst_username:
        try:
            assigned_analyst = User.objects.get(username=assigned_analyst_username)
        except Exception:
            return create_json_response(
                {}, status=400, reason="specified user does not exist")
    else:
        assigned_analyst = None
    update_model_from_json(family, {'assigned_analyst': assigned_analyst}, request.user)

    return create_json_response({
        family.guid: {'assignedAnalyst': {
            'fullName': family.assigned_analyst.get_full_name(),
            'email': family.assigned_analyst.email,
        } if family.assigned_analyst else None}
    })


@login_and_policies_required
def update_family_analysed_by(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
        field_name (string): Family model field name to update
    """

    family = Family.objects.get(guid=family_guid)
    # analysed_by can be edited by anyone with access to the project
    check_project_permissions(family.project, request.user, can_edit=False)

    request_json = json.loads(request.body)
    create_model_from_json(FamilyAnalysedBy, {'family': family, 'data_type': request_json['dataType']}, request.user)

    return create_json_response({
        family.guid: {'analysedBy': list(get_json_for_queryset(family.familyanalysedby_set.all()))}
    })


@login_and_policies_required
def update_family_pedigree_image(request, family_guid):
    """Updates the specified field in the Family model.

    Args:
        family_guid (string): GUID of the family.
    """

    family = Family.objects.get(guid=family_guid)

    # check permission
    check_project_permissions(family.project, request.user, can_edit=True)

    if len(request.FILES) == 0:
        pedigree_image = None
    elif len(request.FILES) > 1:
        return create_json_response({}, status=400, reason='Received {} files'.format(len(request.FILES)))
    else:
        pedigree_image = next(iter((request.FILES.values())))

    update_model_from_json(family, {'pedigree_image': pedigree_image}, request.user)

    updated_image = family.pedigree_image
    if isinstance(family.pedigree_image, ImageFieldFile):
        try:
            updated_image = family.pedigree_image.url
        except Exception:
            updated_image = None

    return create_json_response({
        family.guid: {'pedigreeImage': updated_image}
    })


@login_and_policies_required
def update_family_analysis_groups(request, family_guid):
    family = Family.objects.get(guid=family_guid)
    project = family.project
    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)
    analysis_group_guids = {ag['analysisGroupGuid'] for ag in request_json.get('analysisGroups', [])}
    update_groups = AnalysisGroup.objects.filter(guid__in=analysis_group_guids)

    all_groups = set(family.analysisgroup_set.all())
    all_groups.update(update_groups)

    family.analysisgroup_set.set(update_groups)

    return create_json_response({
        'analysisGroupsByGuid': {
            ag['analysisGroupGuid']: ag for ag in get_json_for_analysis_groups(list(all_groups), project_guid=project.guid)
        },
    })


@login_and_policies_required
def receive_families_table_handler(request, project_guid):
    """Handler for the initial upload of an Excel or .tsv table of families. This handler
    parses the records, but doesn't save them in the database. Instead, it saves them to
    a temporary file and sends a 'uploadedFileId' representing this file back to the client.

    Args:
        request (object): Django request object
        project_guid (string): project GUID
    """

    project = get_project_and_check_pm_permissions(project_guid, request.user)

    def _process_records(records, filename=''):
        column_map = {}
        for i, field in enumerate(records[0]):
            key = field.lower()
            if 'family' in key:
                if 'prev' in key:
                    column_map[PREVIOUS_FAMILY_ID_FIELD] = i
                else:
                    column_map[FAMILY_ID_FIELD] = i
            elif 'display' in key:
                column_map['displayName'] = i
            elif 'phenotype' in key:
                column_map['codedPhenotype'] = i
            elif 'mondo' in key and 'id' in key:
                column_map['mondoId'] = i
            elif 'description' in key:
                column_map['description'] = i
        if FAMILY_ID_FIELD not in column_map:
            raise ValueError('Invalid header, missing family id column')

        return [{column: row[index] if isinstance(index, int) else next((row[i] for i in index if row[i]), None)
                for column, index in column_map.items()} for row in records[1:]]

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, process_records=_process_records)
    except Exception as e:
        return create_json_response({'errors': [str(e)], 'warnings': []}, status=400, reason=str(e))

    prev_fam_ids = {r[PREVIOUS_FAMILY_ID_FIELD] for r in json_records if r.get(PREVIOUS_FAMILY_ID_FIELD)}
    existing_prev_fam_ids = {f.family_id for f in Family.objects.filter(family_id__in=prev_fam_ids, project=project).only('family_id')}
    if len(prev_fam_ids) != len(existing_prev_fam_ids):
        missing_prev_ids = [family_id for family_id in prev_fam_ids if family_id not in existing_prev_fam_ids]
        return create_json_response(
            {'errors': [
                'Could not find families with the following previous IDs: {}'.format(', '.join(missing_prev_ids))
            ], 'warnings': []},
            status=400, reason='Invalid input')

    fam_ids = {r[FAMILY_ID_FIELD] for r in json_records if not r.get(PREVIOUS_FAMILY_ID_FIELD)}
    num_families_to_update = len(prev_fam_ids) + Family.objects.filter(family_id__in=fam_ids, project=project).count()

    num_families = len(json_records)
    num_families_to_create = num_families - num_families_to_update

    info = [
        "{num_families} families parsed from {filename}".format(num_families=num_families, filename=filename),
        "{} new families will be added, {} existing families will be updated".format(num_families_to_create, num_families_to_update),
    ]

    return create_json_response({
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'warnings': [],
        'info': info,
    })

@login_and_policies_required
def create_family_note(request, family_guid):
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    return create_note_handler(
        request, FamilyNote, parent_fields={'family': family}, additional_note_fields=['noteType'],
        get_response_json=lambda note: {'familyNotesByGuid': {note.guid: get_json_for_family_note(note)}},
    )


@login_and_policies_required
def update_family_note(request, family_guid, note_guid):
    return update_note_handler(
        request, FamilyNote, family_guid, note_guid, parent_field='family__guid',
        get_response_json=lambda note: {'familyNotesByGuid': {note_guid: get_json_for_family_note(note)}},
    )


@login_and_policies_required
def delete_family_note(request, family_guid, note_guid):
    return delete_note_handler(
        request, FamilyNote, family_guid, note_guid, parent_field='family__guid',
        get_response_json=lambda: {'familyNotesByGuid': {note_guid: None}},
    )

@login_and_policies_required
def get_family_rna_seq_data(request, family_guid, gene_id):
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    response = defaultdict(lambda: {'individualData': {}})
    tpm_data = RnaSeqTpm.objects.filter(
        gene_id=gene_id, sample__individual__family=family).prefetch_related('sample', 'sample__individual')
    for tpm in tpm_data:
        indiv = tpm.sample.individual
        response[tpm.sample.tissue_type]['individualData'][indiv.display_name or indiv.individual_id] = tpm.tpm

    for tissue in response.keys():
        response[tissue]['rdgData'] = list(
            RnaSeqTpm.objects.filter(sample__tissue_type=tissue, gene_id=gene_id).order_by('tpm').values_list('tpm', flat=True))

    return create_json_response(response)


@login_and_policies_required
def get_family_phenotype_gene_scores(request, family_guid):
    project = Project.objects.get(family__guid=family_guid)
    check_project_permissions(project, request.user)

    phenotype_prioritization = get_phenotype_prioritization([family_guid])
    gene_ids = {gene_id for indiv in phenotype_prioritization.values() for gene_id in indiv.keys()}
    return create_json_response({
        'phenotypeGeneScores': phenotype_prioritization,
        'genesById': get_genes_for_variant_display(gene_ids)
    })
