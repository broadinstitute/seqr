import json
import logging
import requests
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.mail.message import EmailMessage
from django.views.decorators.csrf import csrf_exempt

from matchmaker.models import MatchmakerResult, MatchmakerContactNotes, MatchmakerSubmission
from matchmaker.matchmaker_utils import get_mme_genes_phenotypes, parse_mme_patient, \
    get_submission_json_for_external_match, parse_mme_features, parse_mme_gene_variants
from seqr.models import Individual, SavedVariant
from seqr.utils.communication_utils import post_to_slack
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model, get_json_for_saved_variants, get_json_for_matchmaker_submission
from seqr.views.utils.permissions_utils import check_mme_permissions, check_permissions

from settings import MME_HEADERS, MME_LOCAL_MATCH_URL, MME_EXTERNAL_MATCH_URL, MME_DEFAULT_CONTACT_EMAIL, BASE_URL,  \
    MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, MME_ADD_INDIVIDUAL_URL, MME_DELETE_INDIVIDUAL_URL, API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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

    saved_variants = get_json_for_saved_variants(
        SavedVariant.objects.filter(family=submission.individual.family), add_tags=True, add_details=True)

    gene_ids = set()
    for variant in saved_variants:
        gene_ids.update(variant['transcripts'].keys())

    return _parse_mme_results(
        submission, results, request.user, additional_genes=gene_ids, response_json={
            'savedVariantsByGuid': {variant['variantGuid']: variant for variant in saved_variants}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def search_individual_mme_matches(request, submission_guid):
    """
    Looks for matches for the given submission.
    Returns:
        Status code and results
    """

    submission = MatchmakerSubmission.objects.get(guid=submission_guid)
    check_mme_permissions(submission, request.user)
    return _search_matches(submission, request.user)


def _search_matches(submission, user):
    patient_data = get_submission_json_for_external_match(submission)
    local_result = requests.post(url=MME_LOCAL_MATCH_URL, headers=MME_HEADERS, data=json.dumps(patient_data))
    if local_result.status_code != 200:
        try:
            response_json = local_result.json()
        except Exception:
            response_json = {}
        return create_json_response(response_json, status=local_result.status_code, reason='Error in local match')
    external_result = requests.post(url=MME_EXTERNAL_MATCH_URL, headers=MME_HEADERS, data=json.dumps(patient_data))
    if external_result.status_code != 200:
        try:
            response_json = external_result.json()
        except Exception:
            response_json = {}
        return create_json_response(response_json, status=external_result.status_code, reason='Error in external match')

    results = local_result.json()['results'] + external_result.json()['results']

    initial_saved_results = {
        result.result_data['patient']['id']: result for result in MatchmakerResult.objects.filter(submission=submission)
    }

    new_results = []
    saved_results = {}
    for result in results:
        saved_result = initial_saved_results.get(result['patient']['id'])
        if not saved_result:
            saved_result = MatchmakerResult.objects.create(
                submission=submission,
                result_data=result,
                last_modified_by=user,
            )
            new_results.append(result)
        saved_results[result['patient']['id']] = saved_result

    if new_results:
        try:
            _generate_notification_for_seqr_match(submission, new_results)
        except Exception as e:
            logger.error('Unable to create notification for new MME match: {}'.format(str(e)))

    logger.info('Found {} matches for {} ({} new)'.format(len(results), submission.submission_id, len(new_results)))

    removed_patients = set(initial_saved_results.keys()) - set(saved_results.keys())
    removed_count = 0
    for patient_id in removed_patients:
        saved_result = initial_saved_results[patient_id]
        if saved_result.we_contacted or saved_result.host_contacted or saved_result.comments:
            if not saved_result.match_removed:
                saved_result.match_removed = True
                saved_result.save()
                removed_count += 1
            saved_results[patient_id] = saved_result
        else:
            saved_result.delete()
            removed_count += 1

    if removed_count:
        logger.info('Removed {} old matches for {}'.format(removed_count, submission.submission_id))

    return _parse_mme_results(submission, saved_results.values(), user)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_mme_submission(request, submission_guid=None):
    """
    Create or update the submission for the given individual.
    """
    submission_json = json.loads(request.body)
    phenotypes = submission_json.pop('phenotypes', [])
    gene_variants = submission_json.pop('geneVariants', [])
    if not phenotypes and not gene_variants:
        return create_json_response({}, status=400, reason='Genotypes or phentoypes are required')

    genomic_features = []
    for gene_variant in gene_variants:
        if not gene_variant.get('geneId'):
            return create_json_response({}, status=400, reason='Gene id is required for genomic features')
        feature = {'gene': {'id': gene_variant['geneId']}}
        if 'numAlt' in gene_variant:
            feature['zygosity'] = gene_variant['numAlt'] % 2
        if gene_variant.get('pos'):
            feature['variant'] = {
                'alternateBases': gene_variant['alt'],
                'referenceBases': gene_variant['ref'],
                'referenceName': gene_variant['chrom'],
                'start': gene_variant['pos'],
                'assembly': gene_variant['genomeVersion'],
            }
        genomic_features.append(feature)

    submission_json.update({
        'features': phenotypes,
        'genomicFeatures': genomic_features,
    })

    if submission_guid:
        submission = MatchmakerSubmission.objects.get(guid=submission_guid)
        check_mme_permissions(submission, request.user)
    else:
        individual_guid = submission_json.get('individualGuid')
        if not individual_guid:
            return create_json_response({}, status=400, reason='Individual is required for a new submission')
        individual = Individual.objects.get(guid=individual_guid)
        check_permissions(individual.family.project, request.user)
        submission = MatchmakerSubmission.objects.create(
            individual=individual,
            submission_id=individual.guid,
            label=individual.individual_id,
        )

    update_model_from_json(submission, submission_json, allow_unknown_keys=True)

    # search for new matches
    return _search_matches(submission, request.user)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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

    matchbox_id = submission.submission_id
    response = requests.delete(url=MME_DELETE_INDIVIDUAL_URL, headers=MME_HEADERS, data=json.dumps({'id': matchbox_id}))

    if response.status_code != 200:
        try:
            response_json = response.json()
        except Exception:
            response_json = {}
        return create_json_response(response_json, status=response.status_code, reason=response.content)

    deleted_date = datetime.now()
    submission.deleted_date = deleted_date
    submission.deleted_by = request.user
    submission.save()

    for saved_result in MatchmakerResult.objects.filter(submission=submission):
        if not (saved_result.we_contacted or saved_result.host_contacted or saved_result.comments):
            saved_result.delete()

    return create_json_response({'mmeSubmissionsByGuid': {submission.guid: {'mmeDeletedDate': deleted_date}}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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
    update_model_from_json(result, request_json, allow_unknown_keys=True)

    return create_json_response({
        'mmeResultsByGuid': {matchmaker_result_guid: {'matchStatus': _get_json_for_model(result)}},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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
        to=map(lambda s: s.strip(), request_json['to'].split(',')),
        from_email=MME_DEFAULT_CONTACT_EMAIL,
    )
    try:
        email_message.send()
    except Exception as e:
        message = e.message
        json_body = {}
        if hasattr(e, 'response'):
            message = e.response.content
            try:
                json_body = e.response.json()
            except Exception:
                pass
        return create_json_response(json_body, status=getattr(e, 'status_code', 400), reason=message)

    update_model_from_json(result, {'weContacted': True})

    return create_json_response({
        'mmeResultsByGuid': {matchmaker_result_guid: {'matchStatus': _get_json_for_model(result)}},
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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
    note, _ = MatchmakerContactNotes.objects.get_or_create(institution=institution)

    request_json = json.loads(request.body)
    note.comments = request_json.get('comments', '')
    note.save()

    return create_json_response({
        'mmeContactNotes': {institution: _get_json_for_model(note, user=request.user)},
    })


def _parse_mme_results(submission, saved_results, user, additional_genes=None, response_json=None):
    results = []
    contact_institutions = set()
    for result_model in saved_results:
        result = result_model.result_data
        result['matchStatus'] = _get_json_for_model(result_model)
        results.append(result)
        contact_institutions.add(result['patient']['contact'].get('institution', '').strip().lower())

    additional_hpo_ids = {feature['id'] for feature in (submission.features or []) if feature.get('id')}
    if not additional_genes:
        additional_genes = set()
    additional_genes.update({gene_feature['gene']['id'] for gene_feature in (submission.genomic_features or [])})

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes(
        results, additional_genes=additional_genes, additional_hpo_ids=additional_hpo_ids)

    parsed_results = [_parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids, submission.guid) for result in results]
    parsed_results_gy_guid = {result['matchStatus']['matchmakerResultGuid']: result for result in parsed_results}

    contact_notes = {note.institution: _get_json_for_model(note, user=user)
                     for note in MatchmakerContactNotes.objects.filter(institution__in=contact_institutions)}

    submission_json = get_json_for_matchmaker_submission(
        submission, individual_guid=submission.individual.guid,
        additional_model_fields=['contact_name', 'contact_href', 'submission_id']
    )
    submission_json.update({
        'mmeResultGuids': parsed_results_gy_guid.keys(),
        'phenotypes': parse_mme_features(submission.features, hpo_terms_by_id),
        'geneVariants': parse_mme_gene_variants(submission.genomic_features, gene_symbols_to_ids),
    })

    response = {
        'mmeResultsByGuid': parsed_results_gy_guid,
        'mmeContactNotes': contact_notes,
        'mmeSubmissionsByGuid': {submission.guid: submission_json},
        'individualsByGuid': {submission.individual.guid: {'mmeSubmissionGuid': submission.guid}},
        'genesById': genes_by_id,
    }
    if response_json:
        response.update(response_json)
    return create_json_response(response)


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids, submission_guid):
    parsed_result = parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids, submission_guid)
    parsed_result.update({
        'id': result['patient']['id'],
        'score': result['score']['patient'],
    })
    return parsed_result


def _generate_notification_for_seqr_match(submission, results):
    """
    Generate a notifcation to say that a match happened initiated from a seqr user.
    """
    matches = []
    hpo_terms_by_id, genes_by_id, _ = get_mme_genes_phenotypes(results)
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

    project = submission.individual.family.project
    message = u"""
    A search from a seqr user from project {project} individual {individual_id} had the following new match(es):
    
    {matches}
    
    {host}project/{project_guid}/family_page/{family_guid}/matchmaker_exchange
    """.format(
        project=project.name, individual_id=submission.individual.individual_id, matches='\n\n'.join(matches),
        host=BASE_URL, project_guid=project.guid, family_guid=submission.individual.family.guid,
    )

    post_to_slack(MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, message)
    #  TODO re-enable MME email
    # emails = map(lambda s: s.strip().split('mailto:')[-1], project.mme_contact_url.split(','))
    # email_message = EmailMessage(
    #     subject=u'New matches found for MME submission {} (project: {})'.format(individual.individual_id, project.name),
    #     body=message,
    #     to=[email for email in emails if email != MME_DEFAULT_CONTACT_EMAIL],
    #     from_email=MME_DEFAULT_CONTACT_EMAIL,
    # )
    # email_message.send()
