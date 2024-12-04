"""
APIs used to retrieve and modify Individual fields
"""
import json
from collections import defaultdict
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, Max, Q
from django.db.models.fields.files import ImageFieldFile
from django.db.models.functions import JSONObject, Concat, Upper, Substr

from matchmaker.models import MatchmakerSubmission
from reference_data.models import Omim
from seqr.utils.gene_utils import get_genes_for_variant_display
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.individual_utils import delete_individuals
from seqr.views.utils.json_to_orm_utils import update_family_from_json, update_model_from_json, create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.note_utils import create_note_handler, update_note_handler, delete_note_handler
from seqr.views.utils.orm_to_json_utils import _get_json_for_model,  get_json_for_family_note, get_json_for_samples, \
    get_json_for_matchmaker_submissions, get_json_for_analysis_groups, _get_json_for_families, get_json_for_queryset
from seqr.views.utils.project_context_utils import add_families_context, families_discovery_tags, add_project_tag_types, \
    MME_TAG_NAME
from seqr.models import Family, FamilyAnalysedBy, Individual, FamilyNote, Sample, VariantTag, AnalysisGroup, RnaSeqTpm, \
    PhenotypePrioritization, Project, RnaSeqOutlier, RnaSeqSpliceOutlier, RnaSample
from seqr.views.utils.permissions_utils import check_project_permissions, get_project_and_check_pm_permissions, \
    login_and_policies_required, user_is_analyst, has_case_review_permissions, external_anvil_project_can_edit
from seqr.views.utils.variant_utils import get_phenotype_prioritization, get_omim_intervals_query, DISCOVERY_CATEGORY
from seqr.utils.xpos_utils import get_chrom_pos


FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'

@login_and_policies_required
def family_page_data(request, family_guid):
    families = Family.objects.filter(guid=family_guid)
    family = families.get(guid=family_guid)
    project = family.project
    check_project_permissions(project, request.user)
    is_analyst = user_is_analyst(request.user)
    has_case_review_perm = has_case_review_permissions(project, request.user)

    sample_models = Sample.objects.filter(individual__family=family)
    samples = get_json_for_samples(
        sample_models, project_guid=project.guid, family_guid=family_guid, skip_nested=True, is_analyst=is_analyst
    )
    response = {
        'samplesByGuid': {s['sampleGuid']: s for s in samples}
    }

    add_families_context(response, families, project.guid, request.user, is_analyst, has_case_review_perm)
    family_response = response['familiesByGuid'][family_guid]

    discovery_variants = family.savedvariant_set.filter(varianttag__variant_tag_type__category=DISCOVERY_CATEGORY).values(
        'saved_variant_json__transcripts', 'saved_variant_json__svType', 'xpos', 'xpos_end',
    )
    gene_ids = {
        gene_id for variant in discovery_variants
        for gene_id in (variant['saved_variant_json__transcripts'] or {}).keys()
    }
    discovery_variant_intervals = [dict(zip(
        ['chrom', 'start', 'end_chrom', 'end', 'svType'],
        [*get_chrom_pos(v['xpos']), *get_chrom_pos(v['xpos_end']), v['saved_variant_json__svType']]
    )) for v in discovery_variants]
    omims = Omim.objects.filter(
        get_omim_intervals_query(discovery_variant_intervals) | Q(gene__gene_id__in=gene_ids)
    ).exclude(phenotype_mim_number__isnull=True).order_by('id').distinct()
    omim_map = {}
    _add_parsed_omims(omims, omim_map, intervals=discovery_variant_intervals)
    # Prioritize mim number phenotypes in discovery genes/regions, but if any aren't then include all phenotypes
    missing_discovery_omims = set(family_response['postDiscoveryOmimNumbers']) - set(omim_map.keys())
    if missing_discovery_omims:
        _add_parsed_omims(Omim.objects.filter(phenotype_mim_number__in=missing_discovery_omims), omim_map)

    family_response.update({
        'detailsLoaded': True,
        'postDiscoveryOmimOptions': omim_map,
    })

    tools_by_indiv = defaultdict(list)
    tools_agg = PhenotypePrioritization.objects.filter(individual__family=family).values('individual__guid', 'tool').annotate(
        loadedDate=Max('created_date'),
    ).order_by('tool')
    for agg in tools_agg:
        tools_by_indiv[agg.pop('individual__guid')].append(agg)

    rna_agg = RnaSample.objects.filter(individual__family=family, is_active=True).values('individual__guid').annotate(
        loadedDate=Max('created_date'), dataTypes=ArrayAgg('data_type', distinct=True, ordering='data_type'),
    )
    rna_samples_by_individual = {agg.pop('individual__guid'): agg for agg in rna_agg}

    submissions = get_json_for_matchmaker_submissions(MatchmakerSubmission.objects.filter(individual__family=family))
    individual_mme_submission_guids = {s['individualGuid']: s['submissionGuid'] for s in submissions}
    for individual in response['individualsByGuid'].values():
        individual['mmeSubmissionGuid'] = individual_mme_submission_guids.get(individual['individualGuid'])
        individual['phenotypePrioritizationTools'] = tools_by_indiv.get(individual['individualGuid'], [])
        individual['rnaSample'] = rna_samples_by_individual.get(individual['individualGuid'])
    response['mmeSubmissionsByGuid'] = {s['submissionGuid']: s for s in submissions}

    return create_json_response(response)


def _intervals_overlap(interval1, interval2):
    return interval1['chrom'] == interval2['chrom'] and (
            (interval2['start'] <= interval1['start'] <= interval2['end']) or
            (interval2['start'] <= interval1['end'] <= interval2['end']) or
            (interval1['start'] <= interval2['start'] <= interval1['end']) or
            (interval1['start'] <= interval2['end'] <= interval1['end']))


def _add_parsed_omims(omims, omim_map, intervals=None):
    for o in get_json_for_queryset(omims, nested_fields=[{'key': 'geneSymbol', 'fields': ['gene', 'gene_symbol']}]):
        if intervals is not None and (not (o['geneSymbol'] or any(_intervals_overlap(o, variant) for variant in intervals))):
            continue
        mim_number = o['phenotypeMimNumber']
        if mim_number not in omim_map:
            omim_map[mim_number] = {'phenotypeMimNumber': mim_number, 'phenotypes': []}
        omim_map[mim_number]['phenotypes'].append(o)


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
    add_project_tag_types(response['projectsByGuid'], project=project)

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

    family_guids = [f.get('familyGuid') for f in modified_families]
    family_models = {f.guid: f for f in Family.objects.filter(project=project, guid__in=family_guids)}
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

    updated_family_ids = []
    for fields in modified_families:
        family = family_models[fields['familyGuid']]
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
    immutable_keys = [] if external_anvil_project_can_edit(family.project, request.user) else ['family_id']
    update_family_from_json(family, request_json, user=request.user, allow_unknown_keys=True, immutable_keys=[
        'display_name',
    ] + immutable_keys)

    return create_json_response({
        family.guid: _get_json_for_model(family, user=request.user, process_result=_set_display_name)
    })


def _set_display_name(family_json, family_model):
    family_json['displayName'] = family_model.display_name or family_model.family_id


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


EXTERNAL_DATA_LOOKUP = {v: k for k, v in Family.EXTERNAL_DATA_CHOICES}
PARSE_FAMILY_TABLE_FIELDS = {
    'externalData': lambda data_type: [EXTERNAL_DATA_LOOKUP[dt.strip()] for dt in (data_type or '').split(';') if dt],
}


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
            elif 'external' in key and 'data' in key:
                column_map['externalData'] = i
        if FAMILY_ID_FIELD not in column_map:
            raise ValueError('Invalid header, missing family id column')

        parsed_records = [{column: PARSE_FAMILY_TABLE_FIELDS.get(column, lambda v: v)(row[index])
                for column, index in column_map.items()} for row in records[1:]]
        family_ids = [r.get(PREVIOUS_FAMILY_ID_FIELD) or r[FAMILY_ID_FIELD] for r in parsed_records]
        family_guid_map = dict(
            Family.objects.filter(family_id__in=family_ids, project=project).values_list('family_id', 'guid')
        )
        return [{
            'familyGuid': family_guid_map.get(r.get(PREVIOUS_FAMILY_ID_FIELD) or r[FAMILY_ID_FIELD]),
            **r,
        } for r in parsed_records]

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, process_records=_process_records)
    except Exception as e:
        return create_json_response({'errors': [str(e)], 'warnings': []}, status=400, reason=str(e))

    missing_guid_records = [r for r in json_records if not r['familyGuid']]
    if missing_guid_records:
        missing_prev_ids = [r[PREVIOUS_FAMILY_ID_FIELD] for r in missing_guid_records if r.get(PREVIOUS_FAMILY_ID_FIELD)]
        missing_curr_ids = [r[FAMILY_ID_FIELD] for r in missing_guid_records if not r.get(PREVIOUS_FAMILY_ID_FIELD)]
        errors = []
        if missing_prev_ids:
            errors.append('Could not find families with the following previous IDs: {}'.format(', '.join(missing_prev_ids)))
        if missing_curr_ids:
            errors.append('Could not find families with the following current IDs: {}'.format(', '.join(missing_curr_ids)))
        return create_json_response(
            {'errors': errors, 'warnings': []},
            status=400, reason='Invalid input')

    info = [
       f"{len(json_records)} exisitng families parsed from {filename}",
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
        'genesById': get_genes_for_variant_display(gene_ids, project.genome_version),
    })
