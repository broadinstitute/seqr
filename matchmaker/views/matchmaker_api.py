import json
import requests
from datetime import datetime
from django.core.mail.message import EmailMessage
from django.db.models import prefetch_related_objects, Q

from matchmaker.models import MatchmakerResult, MatchmakerContactNotes, MatchmakerSubmission, MatchmakerSubmissionGenes, \
    MatchmakerIncomingQuery
from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_results, parse_mme_patient, \
    get_submission_json_for_external_match, parse_mme_features, get_submission_gene_variants, get_mme_matches, \
    get_gene_ids_for_feature, validate_patient_data, get_hpo_terms_by_id, MME_DISCLAIMER
from seqr.models import Individual, SavedVariant
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json, \
    create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model, get_json_for_saved_variants_with_tags, \
    get_json_for_matchmaker_submission, get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import check_mme_permissions, check_project_permissions, analyst_required, \
    has_project_permissions, login_and_policies_required, get_project_and_check_permissions

from settings import BASE_URL, MME_ACCEPT_HEADER, MME_NODES, MME_DEFAULT_CONTACT_EMAIL, \
    MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, MME_SLACK_ALERT_NOTIFICATION_CHANNEL

logger = SeqrLogger(__name__)


MME_NODES_BY_NAME = {node['name']: node for node in MME_NODES.values() if node.get('url')}
MAX_SUBMISSION_VARIANTS = 5


@login_and_policies_required
def get_individual_mme_matches(request, submission_guid):
    """
    Looks for matches for the given submission. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
    submission = MatchmakerSubmission.objects.get(guid=submission_guid)
    check_mme_permissions(submission, request.user)

    results = MatchmakerResult.objects.filter(submission=submission)

    response_json = get_json_for_saved_variants_with_tags(
        SavedVariant.objects.filter(family=submission.individual.family), add_details=True)

    gene_ids = set()
    for variant in response_json['savedVariantsByGuid'].values():
        gene_ids.update(list(variant.get('transcripts', {}).keys()))

    hpo_terms_by_id = get_hpo_terms_by_id(
        {feature['id'] for feature in (submission.features or []) if feature.get('id')})
    phenotypes = parse_mme_features(submission.features, hpo_terms_by_id)
    response_json.update(_get_submission_detail_response(submission, phenotypes))

    return _parse_mme_results(
        submission, results, request.user, additional_genes=gene_ids, response_json=response_json)


@login_and_policies_required
def get_mme_nodes(request):
    return create_json_response({'mmeNodes': list(MME_NODES_BY_NAME.keys())})


@login_and_policies_required
def search_local_individual_mme_matches(request, submission_guid):
    return _search_node_matches(submission_guid, 'Broad MME', request.user, is_local=True)


@login_and_policies_required
def search_individual_mme_matches(request, submission_guid, node):
    incoming_query = MatchmakerIncomingQuery.objects.get(guid=request.GET['incomingQueryGuid'])
    return _search_node_matches(submission_guid, node, request.user, incoming_query=incoming_query)


def _search_node_matches(submission_guid, node, user, is_local=False, incoming_query=None):
    submission = MatchmakerSubmission.objects.get(guid=submission_guid)
    check_mme_permissions(submission, user)
    patient_data = get_submission_json_for_external_match(submission)

    response_json = {}
    if is_local:
        results, incoming_query = get_mme_matches(patient_data, user=user, originating_submission=submission)
        response_json['incomingQueryGuid'] = incoming_query.guid
    else:
        results = _search_external_matches(MME_NODES_BY_NAME[node], patient_data, user)

    result_patient_ids = [result['patient']['id'] for result in results]
    initial_saved_results = {
        result.result_data['patient']['id']: result
        for result in MatchmakerResult.objects.filter(submission=submission, result_data__patient__id__in=result_patient_ids)
    }

    local_result_submissions = {
        s.submission_id: s for s in MatchmakerSubmission.objects.filter(matchmakerresult__originating_submission=submission)
    } if is_local else {}

    new_count = 0
    saved_results = {}
    for result in results:
        result_patient_id = result['patient']['id']
        saved_result = initial_saved_results.get(result_patient_id)
        if not saved_result:
            saved_result = create_model_from_json(MatchmakerResult, {
                'submission': submission,
                'originating_submission': local_result_submissions.get(result_patient_id),
                'originating_query': incoming_query,
                'result_data': result,
                'last_modified_by': user,
            }, user)
            new_count += 1
        else:
            update_model_from_json(
                saved_result, {'result_data': result, 'match_removed': False}, user, updated_fields={'last_modified_date'}
            )
        saved_results[result['patient']['id']] = saved_result

    logger.info('Found {} matches in {} for {} ({} new)'.format(len(results), node, submission.submission_id, new_count), user)

    return _parse_mme_results(submission, list(saved_results.values()), user, response_json=response_json)


@login_and_policies_required
def finalize_mme_search(request, submission_guid):
    submission = MatchmakerSubmission.objects.get(guid=submission_guid)
    user = request.user
    check_mme_permissions(submission, user)

    originating_query = MatchmakerIncomingQuery.objects.get(guid=request.GET['incomingQueryGuid'])
    submission_results = MatchmakerResult.objects.filter(submission=submission)

    new_results = submission_results.filter(originating_query=originating_query).order_by('created_date')
    if new_results:
        try:
            _generate_notification_for_seqr_match(submission, [r.result_data for r in new_results])
        except Exception as e:
            logger.error('Unable to create notification for new MME match: {}'.format(str(e)), user)

    removed_results = submission_results.filter(
        # Any matches will have been updated so their modified timestamp will be after the query was submitted
        last_modified_date__lt=originating_query.created_date,
    )

    total_results = submission_results.count() - removed_results.count()
    logger.info('Found {} total matches for {} ({} new)'.format(total_results, submission.submission_id, len(new_results)), user)

    updated_results_json = {}
    to_remove_results = removed_results.filter(match_removed=False)
    if to_remove_results:
        removed_count = to_remove_results.count()
        is_deletable_filter = Q(we_contacted=False) & Q(host_contacted=False) & (
                Q(comments__isnull=True) | Q(comments__exact=''))
        to_delete = to_remove_results.filter(is_deletable_filter)
        if to_delete:
            updated_results_json.update({r.guid: None for r in to_delete})
            MatchmakerResult.bulk_delete(user, queryset=to_delete)

        to_remove = to_remove_results.exclude(is_deletable_filter)
        if to_remove:
            updated = MatchmakerResult.bulk_update(user, {'match_removed': True}, queryset=to_remove)
            updated_results_json.update({
                r.guid: {'matchStatus':  _get_json_for_model(r)}
                for r in MatchmakerResult.objects.filter(guid__in=updated)
            })

        logger.info('Removed {} old matches for {}'.format(removed_count, submission.submission_id), user)

    return create_json_response({'mmeResultsByGuid': updated_results_json})


def _search_external_matches(node, patient_data, user):
    body = {'_disclaimer': MME_DISCLAIMER}
    body.update(patient_data)
    external_results = []
    submission_gene_ids = set()
    for feature in patient_data['patient'].get('genomicFeatures', []):
        submission_gene_ids.update(get_gene_ids_for_feature(feature, {}))

    headers = {
        'X-Auth-Token': node['token'],
        'Accept': MME_ACCEPT_HEADER,
        'Content-Type': MME_ACCEPT_HEADER,
        'Content-Language': 'en-US',
    }
    try:
        external_result = requests.post(url=node['url'], headers=headers, data=json.dumps(body), timeout=300)
        if external_result.status_code != 200:
            try:
                message = external_result.json().get('message')
            except Exception:
                message = external_result.content.decode('utf-8')
            error_message = '{} ({})'.format(message or 'Error', external_result.status_code)
            raise Exception(error_message)

        node_results = external_result.json()['results']
        logger.info('Found {} matches from {}'.format(len(node_results), node['name']), user)
        if node_results:
            _, _, gene_symbols_to_ids = get_mme_genes_phenotypes_for_results(node_results)
            invalid_results = []
            malformed_results = []
            for result in node_results:
                try:
                    validate_patient_data(result)
                    if (not submission_gene_ids) or \
                            _is_valid_external_match(result, submission_gene_ids, gene_symbols_to_ids):
                        external_results.append(result)
                    else:
                        invalid_results.append(result)
                except ValueError:
                    malformed_results.append(result)
            if malformed_results:
                _report_external_mme_error(node['name'], 'Received invalid results for {}'.format(patient_data['patient']['label']), malformed_results, user)
            if invalid_results:
                error_message = 'Received {} invalid matches from {}'.format(len(invalid_results), node['name'])
                logger.warning(error_message, user)
    except Exception as e:
        _report_external_mme_error(node['name'], str(e), patient_data, user, raise_exception=True)

    return external_results


def _is_valid_external_match(result, submission_gene_ids, gene_symbols_to_ids):
    for feature in result.get('patient', {}).get('genomicFeatures', []):
        if any(gene_id in submission_gene_ids for gene_id in get_gene_ids_for_feature(feature, gene_symbols_to_ids)):
            return True
    return False


def _report_external_mme_error(node_name, error, detail, user, raise_exception=False):
    error_message = 'Error searching in {}: {}'.format(node_name, error)
    slack_message = '{}\n```{}```'.format(error_message, json.dumps(detail, indent=2))
    safe_post_to_slack(MME_SLACK_ALERT_NOTIFICATION_CHANNEL, slack_message)
    if raise_exception:
        e = ErrorsWarningsException([error_message])
        e.info = detail
        raise e
    else:
        logger.warning(error_message, user, detail=detail)


@login_and_policies_required
def update_mme_submission(request, submission_guid=None):
    """
    Create or update the submission for the given individual.
    """
    submission_json = json.loads(request.body)
    phenotypes = submission_json.pop('phenotypes', [])
    gene_variants = submission_json.pop('geneVariants', [])
    if not phenotypes and not gene_variants:
        return create_json_response({}, status=400, reason='Genotypes or phenotypes are required')
    if not all(gene_variant.get('geneId') and gene_variant.get('variantGuid') for gene_variant in gene_variants):
        return create_json_response({}, status=400, reason='Gene and variant IDs are required for genomic features')
    if len(gene_variants) > MAX_SUBMISSION_VARIANTS:
        return create_json_response({}, status=400, reason=f'No more than {MAX_SUBMISSION_VARIANTS} variants can be submitted per individual')

    submission_json.update({
        'features': phenotypes,
        'deletedDate': None,
        'deletedBy': None,
    })

    if submission_guid:
        submission = MatchmakerSubmission.objects.get(guid=submission_guid)
        check_mme_permissions(submission, request.user)
    else:
        individual_guid = submission_json.get('individualGuid')
        if not individual_guid:
            return create_json_response({}, status=400, reason='Individual is required for a new submission')
        individual = Individual.objects.get(guid=individual_guid)
        check_project_permissions(individual.family.project, request.user)
        submission = create_model_from_json(MatchmakerSubmission, {
            'individual': individual,
            'submission_id': individual.guid,
            'label': individual.individual_id,
        }, request.user)

    update_model_from_json(submission, submission_json, user=request.user, allow_unknown_keys=True)

    new_gene_variants = {(gene_variant['geneId'], gene_variant['variantGuid']) for gene_variant in gene_variants}
    existing_submission_genes = {
        (s.gene_id, s.saved_variant.guid): s
        for s in submission.matchmakersubmissiongenes_set.all().select_related('saved_variant')
    }
    existing_gv_keys = set(existing_submission_genes.keys())
    to_delete = existing_gv_keys - new_gene_variants
    to_create = new_gene_variants - existing_gv_keys
    saved_variants = {
        sv.guid: sv for sv in SavedVariant.objects.filter(guid__in=[gv[1] for gv in to_create])
    }
    for gene_id, variant_guid in to_create:
        MatchmakerSubmissionGenes.objects.create(
            matchmaker_submission=submission,
            saved_variant=saved_variants[variant_guid],
            gene_id=gene_id,
        )
    for gv in to_delete:
        existing_submission_genes[gv].delete()

    response = _get_submission_detail_response(submission, phenotypes)
    if not submission_guid:
        response['individualsByGuid'] = {submission.individual.guid: {'mmeSubmissionGuid': submission.guid}}
    return create_json_response(response)


def _get_submission_detail_response(submission, phenotypes):
    submission_response = get_json_for_matchmaker_submission(submission)
    submission_response.update({
        'phenotypes': phenotypes,
        'geneVariants': get_submission_gene_variants(submission),
    })
    return {
        'mmeSubmissionsByGuid': {submission.guid: submission_response},
    }


@login_and_policies_required
def delete_mme_submission(request, submission_guid):
    """
    Create or update the submission for the given individual.
    """
    submission = MatchmakerSubmission.objects.get(guid=submission_guid)
    check_mme_permissions(submission, request.user)

    if submission.deleted_date:
        return create_json_response(
            {}, status=402,
            reason='Matchmaker submission has already been deleted for {}'.format(submission.individual.individual_id),
        )

    deleted_date = datetime.now()
    update_model_from_json(submission, {'deleted_date': deleted_date, 'deleted_by': request.user}, request.user)

    MatchmakerSubmissionGenes.objects.filter(matchmaker_submission=submission).delete()

    for saved_result in MatchmakerResult.objects.filter(submission=submission):
        if not (saved_result.we_contacted or saved_result.host_contacted or saved_result.comments):
            saved_result.delete_model(request.user, user_can_delete=True)

    return create_json_response({'mmeSubmissionsByGuid': {submission.guid: {'deletedDate': deleted_date}}})


@login_and_policies_required
def update_mme_result_status(request, matchmaker_result_guid):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
    result = MatchmakerResult.objects.get(guid=matchmaker_result_guid)
    check_mme_permissions(result.submission, request.user)

    request_json = json.loads(request.body)
    update_model_from_json(
        result, request_json, user=request.user, allow_unknown_keys=True, immutable_keys=['originating_submission'])

    return create_json_response({
        'mmeResultsByGuid': {matchmaker_result_guid: {'matchStatus': _get_json_for_model(result)}},
    })


@login_and_policies_required
def send_mme_contact_email(request, matchmaker_result_guid):
    """
    Sends the given email and updates the contacted status for the match
    Args:
        matchmaker_result_guid
    Returns:
        Status code and results
    """
    result = MatchmakerResult.objects.get(guid=matchmaker_result_guid)
    check_mme_permissions(result.submission, request.user)

    request_json = json.loads(request.body)
    email_message = EmailMessage(
        subject=request_json['subject'],
        body=request_json['body'],
        to=[s.strip() for s in request_json['to'].split(',')],
        from_email=MME_DEFAULT_CONTACT_EMAIL,
    )
    try:
        email_message.send()
    except Exception as e:
        message = str(e)
        json_body = {}
        if hasattr(e, 'response'):
            message = e.response.content
            try:
                json_body = e.response.json()
            except Exception:
                json_body = {'error': message}
        return create_json_response(json_body, status=getattr(e, 'status_code', 400), reason=message)

    update_model_from_json(result, {'weContacted': True}, user=request.user)

    return create_json_response({
        'mmeResultsByGuid': {matchmaker_result_guid: {'matchStatus': _get_json_for_model(result)}},
    })


@login_and_policies_required
def update_mme_project_contact(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    contact = (request_json.get('contact') or '').strip()
    if not contact:
        return create_json_response({'error': 'Contact is required'}, status=400)

    submissions = MatchmakerSubmission.objects.filter(individual__family__project=project).exclude(
        contact_href__contains=contact)
    for submission in submissions:
        submission.contact_href = f'{submission.contact_href},{contact}' if submission.contact_href else contact
        submission.save()

    return create_json_response({
        'mmeSubmissionsByGuid': {s['submissionGuid']: s for s in get_json_for_matchmaker_submissions(submissions)},
    })


@analyst_required
def update_mme_contact_note(request, institution):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
    institution = institution.strip().lower()
    request_json = json.loads(request.body)
    note, _ = get_or_create_model_from_json(
        MatchmakerContactNotes,
        create_json={'institution': institution},
        update_json={'comments': request_json.get('comments', '')},
        user=request.user)

    return create_json_response({
        'mmeContactNotes': {institution: _get_json_for_model(note, user=request.user)},
    })


def _parse_mme_results(submission, saved_results, user, additional_genes=None, response_json=None):
    results = []
    contact_institutions = set()
    prefetch_related_objects(saved_results, 'originating_submission__individual__family__project')
    for result_model in saved_results:
        result = result_model.result_data
        result['matchStatus'] = _get_json_for_model(result_model)
        if result_model.originating_submission:
            originating_family = result_model.originating_submission.individual.family
            if has_project_permissions(originating_family.project, user):
                result['originatingSubmission'] = {
                    'originatingSubmissionGuid': result_model.originating_submission.guid,
                    'familyGuid': originating_family.guid,
                    'projectGuid': originating_family.project.guid,
                }
        results.append(result)
        contact_institutions.add(result['patient']['contact'].get('institution', '').strip().lower())

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes_for_results(
        results, additional_genes=additional_genes)

    parsed_results = [_parse_mme_result(res, hpo_terms_by_id, gene_symbols_to_ids, submission.guid) for res in results]
    parsed_results_gy_guid = {result['matchStatus']['matchmakerResultGuid']: result for result in parsed_results}

    contact_notes = {note.institution: _get_json_for_model(note, user=user)
                     for note in MatchmakerContactNotes.objects.filter(institution__in=contact_institutions)}

    response = {
        'mmeResultsByGuid': parsed_results_gy_guid,
        'mmeContactNotes': contact_notes,
        'genesById': genes_by_id,
    }
    if response_json:
        response.update(response_json)
    return create_json_response(response)


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids, submission_guid):
    parsed_result = parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids, submission_guid)
    parsed_result.update({
        'id': result['patient']['id'],
        'score': result.get('score', {}).get('patient'),
    })
    return parsed_result


def _generate_notification_for_seqr_match(submission, results):
    """
    Generate a notifcation to say that a match happened initiated from a seqr user.
    """
    matches = []
    hpo_terms_by_id, genes_by_id, _ = get_mme_genes_phenotypes_for_results(results)
    for result in results:
        patient = result['patient']

        gene_message = ''
        if patient.get('genomicFeatures'):
            gene_symbols = set()
            for gene in patient['genomicFeatures']:
                gene_symbol = gene['gene']['id']
                if gene_symbol.startswith('ENSG'):
                    gene_symbol = genes_by_id.get(gene_symbol, {}).get('geneSymbol', gene_symbol)
                gene_symbols.add(gene_symbol)

            gene_message = ' with genes {}'.format(' '.join(sorted(gene_symbols)))

        phenotypes_message = ''
        if patient.get('features'):
            phenotypes_message = ' with phenotypes {}'.format(' '.join(
                ['{} ({})'.format(feature['id'], hpo_terms_by_id.get(feature['id'])) for feature in patient['features']]
            ))

        matches.append(' - From {contact} at institution {institution}{gene_message}{phenotypes_message}.'.format(
            contact=patient['contact'].get('name', '(none given)'),
            institution=patient['contact'].get('institution', '(none given)'),
            gene_message=gene_message, phenotypes_message=phenotypes_message,
        ))

    individual = submission.individual
    project = individual.family.project
    message = """
    A search from a seqr user from project {project} individual {individual_id} had the following new match(es):
    
    {matches}
    
    {host}project/{project_guid}/family_page/{family_guid}/matchmaker_exchange
    """.format(
        project=project.name, individual_id=individual.individual_id, matches='\n\n'.join(matches),
        host=BASE_URL, project_guid=project.guid, family_guid=submission.individual.family.guid,
    )
    safe_post_to_slack(MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, message)
    emails = [s.strip().split('mailto:')[-1] for s in submission.contact_href.split(',')]
    email_message = EmailMessage(
        subject='New matches found for MME submission {} (project: {})'.format(individual.individual_id, project.name),
        body=message,
        to=[email for email in emails if email != MME_DEFAULT_CONTACT_EMAIL],
        from_email=MME_DEFAULT_CONTACT_EMAIL,
    )
    email_message.send()
