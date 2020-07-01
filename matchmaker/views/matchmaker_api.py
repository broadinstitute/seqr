from __future__ import unicode_literals

import json
import logging
import requests
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.mail.message import EmailMessage
from django.views.decorators.csrf import csrf_exempt

from matchmaker.models import MatchmakerResult, MatchmakerContactNotes, MatchmakerSubmission
from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_results, parse_mme_patient, \
    get_submission_json_for_external_match, parse_mme_features, parse_mme_gene_variants, get_mme_matches, \
    get_gene_ids_for_feature, MME_DISCLAIMER
from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Individual, SavedVariant
from seqr.utils.communication_utils import post_to_slack
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model, get_json_for_saved_variants_with_tags, \
    get_json_for_matchmaker_submission
from seqr.views.utils.permissions_utils import check_mme_permissions, check_project_permissions

from settings import BASE_URL, API_LOGIN_REQUIRED_URL, MME_ACCEPT_HEADER, MME_NODES, MME_DEFAULT_CONTACT_EMAIL, \
    MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, MME_SLACK_ALERT_NOTIFICATION_CHANNEL

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

    response_json = get_json_for_saved_variants_with_tags(
        SavedVariant.objects.filter(family=submission.individual.family), add_details=True)

    gene_ids = set()
    for variant in response_json['savedVariantsByGuid'].values():
        gene_ids.update(list(variant['transcripts'].keys()))

    return _parse_mme_results(
        submission, results, request.user, additional_genes=gene_ids, response_json=response_json)


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

    nodes_to_query = [node for node in MME_NODES.values() if node.get('url')]
    if not nodes_to_query:
        message = 'No external MME nodes are configured'
        return create_json_response({'message': message}, status=400, reason=message)

    external_results = _search_external_matches(nodes_to_query, patient_data)
    local_results, incoming_query = get_mme_matches(patient_data, user=user)

    results = local_results + external_results

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
                originating_query=incoming_query,
                result_data=result,
                last_modified_by=user,
            )
            new_results.append(result)
        else:
            saved_result.result_data = result
            saved_result.save()
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

    return _parse_mme_results(submission, list(saved_results.values()), user)


def _search_external_matches(nodes_to_query, patient_data):
    body = {'_disclaimer': MME_DISCLAIMER}
    body.update(patient_data)
    external_results = []
    submission_gene_ids = set()
    for feature in patient_data['patient'].get('genomicFeatures', []):
        submission_gene_ids.update(get_gene_ids_for_feature(feature, {}))

    for node in nodes_to_query:
        headers = {
            'X-Auth-Token': node['token'],
            'Accept': MME_ACCEPT_HEADER,
            'Content-Type': MME_ACCEPT_HEADER,
            'Content-Language': 'en-US',
        }
        try:
            external_result = requests.post(url=node['url'], headers=headers, data=json.dumps(body))
            if external_result.status_code != 200:
                try:
                    message = external_result.json().get('message')
                except Exception:
                    message = external_result.content.decode('utf-8')
                error_message = '{} ({})'.format(message or 'Error', external_result.status_code)
                raise Exception(error_message)

            node_results = external_result.json()['results']
            logger.info('Found {} matches from {}'.format(len(node_results), node['name']))
            if node_results:
                _, _, gene_symbols_to_ids = get_mme_genes_phenotypes_for_results(node_results)
                invalid_results = []
                for result in node_results:
                    if (not submission_gene_ids) or \
                            _is_valid_external_match(result, submission_gene_ids, gene_symbols_to_ids):
                        external_results.append(result)
                    else:
                        invalid_results.append(result)
                if invalid_results:
                    error_message = 'Received {} invalid matches from {}'.format(len(invalid_results), node['name'])
                    logger.error(error_message)
        except Exception as e:
            error_message = 'Error searching in {}: {}\n(Patient info: {})'.format(
                node['name'], str(e), json.dumps(patient_data))
            logger.error(error_message)
            post_to_slack(MME_SLACK_ALERT_NOTIFICATION_CHANNEL, error_message)

    return external_results


def _is_valid_external_match(result, submission_gene_ids, gene_symbols_to_ids):
    for feature in result.get('patient', {}).get('genomicFeatures', []):
        if any(gene_id in submission_gene_ids for gene_id in get_gene_ids_for_feature(feature, gene_symbols_to_ids)):
            return True
    return False


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
            feature['zygosity'] = gene_variant['numAlt']
        if gene_variant.get('pos'):
            genome_version = gene_variant['genomeVersion']
            feature['variant'] = {
                'alternateBases': gene_variant['alt'],
                'referenceBases': gene_variant['ref'],
                'referenceName': gene_variant['chrom'],
                'start': gene_variant['pos'],
                'assembly': GENOME_VERSION_LOOKUP.get(genome_version, genome_version),
            }
        genomic_features.append(feature)

    submission_json.update({
        'features': phenotypes,
        'genomicFeatures': genomic_features,
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

    deleted_date = datetime.now()
    submission.deleted_date = deleted_date
    submission.deleted_by = request.user
    submission.save()

    for saved_result in MatchmakerResult.objects.filter(submission=submission):
        if not (saved_result.we_contacted or saved_result.host_contacted or saved_result.comments):
            saved_result.delete()

    return create_json_response({'mmeSubmissionsByGuid': {submission.guid: {'deletedDate': deleted_date}}})


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
                json_body = {'message':message}
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

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes_for_results(
        results, additional_genes=additional_genes, additional_hpo_ids=additional_hpo_ids)

    parsed_results = [_parse_mme_result(res, hpo_terms_by_id, gene_symbols_to_ids, submission.guid) for res in results]
    parsed_results_gy_guid = {result['matchStatus']['matchmakerResultGuid']: result for result in parsed_results}

    contact_notes = {note.institution: _get_json_for_model(note, user=user)
                     for note in MatchmakerContactNotes.objects.filter(institution__in=contact_institutions)}

    submission_json = get_json_for_matchmaker_submission(
        submission, individual_guid=submission.individual.guid,
        additional_model_fields=['contact_name', 'contact_href', 'submission_id']
    )
    submission_json.update({
        'mmeResultGuids': list(parsed_results_gy_guid.keys()),
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

    post_to_slack(MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, message)
    emails = [s.strip().split('mailto:')[-1] for s in submission.contact_href.split(',')]
    email_message = EmailMessage(
        subject='New matches found for MME submission {} (project: {})'.format(individual.individual_id, project.name),
        body=message,
        to=[email for email in emails if email != MME_DEFAULT_CONTACT_EMAIL],
        from_email=MME_DEFAULT_CONTACT_EMAIL,
    )
    email_message.send()
