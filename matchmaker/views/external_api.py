import json

import logging
from django.core.mail.message import EmailMessage
from django.views.decorators.csrf import csrf_exempt

from matchmaker.models import MatchmakerResult
from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_results, get_mme_metrics, get_mme_matches, \
    validate_patient_data, MME_DISCLAIMER

from seqr.utils.communication_utils import safe_post_to_slack
from seqr.views.utils.json_utils import create_json_response

from settings import MME_ACCEPT_HEADER, MME_NODES, MME_SLACK_MATCH_NOTIFICATION_CHANNEL, MME_DEFAULT_CONTACT_EMAIL, \
    BASE_URL

logger = logging.getLogger(__name__)


"""
ENDPOINTS IN THIS FILE ARE ACCESSED BY NON_SEQR USERS. BE CAREFUL WHEN EDITING NOT TO MAKE BREAKING CHANGES
"""


def authenticate_mme_request(view_func):
    def _wrapped_view(request, *args, **kwargs):
        accept_header = request.META.get('HTTP_ACCEPT')
        if accept_header != MME_ACCEPT_HEADER:
            return create_json_response({
                'error': 'Not Acceptable',
                'message': 'unsupported API version, supported versions=[1.0]',
            }, status=406)

        auth_token = request.META.get('HTTP_X_AUTH_TOKEN')
        originating_node = MME_NODES.get(auth_token)
        if not originating_node:
            return create_json_response({
                'error': 'Unauthorized',
                'message': 'authentication failed',
            }, status=401)

        return view_func(request, originating_node['name'], *args, **kwargs)
    return csrf_exempt(_wrapped_view)


@authenticate_mme_request
def mme_metrics_proxy(request, originating_node_name):
    """
    -Proxies public metrics endpoint
    Returns:
        Metric JSON from matchbox
    """
    logger.info('Received MME metrics request from {}'.format(originating_node_name))
    return create_json_response({'metrics': get_mme_metrics()})


@authenticate_mme_request
def mme_match_proxy(request, originating_node_name):
    """
    -Looks for matches for the given individual ONLY in the local MME DB.
    -Expects a single patient (as per MME spec) in the POST

    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results (as per MME spec), returns raw results from MME Server
    """
    logger.info('Received MME match request from {}'.format(originating_node_name))

    try:
        query_patient_data = json.loads(request.body)
        validate_patient_data(query_patient_data)
    except json.JSONDecodeError:
        return create_json_response({'error': 'No JSON object could be decoded'}, status = 400)
    except Exception as e:
        return create_json_response({'error': str(e)}, status=400)

    results, incoming_query = get_mme_matches(
        patient_data=query_patient_data, origin_request_host=originating_node_name,
    )

    _safe_generate_notification_for_incoming_match(results, incoming_query, originating_node_name, query_patient_data)

    return create_json_response({
        'results': sorted(results, key=lambda result: result['score']['patient'], reverse=True),
        '_disclaimer': MME_DISCLAIMER,
    })


def _safe_generate_notification_for_incoming_match(results, incoming_query, incoming_request_node, incoming_patient):
    """
    Generate a SLACK notifcation to say that a VALID match request came in and the following
    results were sent back. If Slack is not supported, a message is not sent, but details persisted.

    Args:
        response_from_matchbox (python requests object): contains the response from matchbox
        incoming_request (Django request object): The request that came into the view
        incoming_patient (JSON): The query patient JSON structure from outside MME node that was matched with
    """
    incoming_patient_id = incoming_patient['patient']['id']

    logger.info('{} MME matches found for patient {} from {}'.format(
        len(results), incoming_patient_id, incoming_request_node)
    )

    institution = incoming_patient['patient']['contact'].get('institution', incoming_request_node)
    contact_href = incoming_patient['patient']['contact'].get('href', '(sorry I was not able to read the information given for URL)')

    if not results:
        message_template = """A match request for {patient_id} came in from {institution} today.
        The contact information given was: {contact}.
        We didn't find any individuals in matchbox that matched that query well, *so no results were sent back*."""
        safe_post_to_slack(MME_SLACK_MATCH_NOTIFICATION_CHANNEL, message_template.format(
            institution=institution, patient_id=incoming_patient_id, contact=contact_href
        ))
        return

    new_matched_results = MatchmakerResult.objects.filter(
        originating_query=incoming_query).prefetch_related('submission')
    if not new_matched_results:
        message_template = """A match request for {patient_id} came in from {institution} today.
        The contact information given was: {contact}.
        We found {existing_results} existing matching individuals but no new ones, *so no results were sent back*."""
        safe_post_to_slack(MME_SLACK_MATCH_NOTIFICATION_CHANNEL, message_template.format(
            institution=institution, patient_id=incoming_patient_id, contact=contact_href, existing_results=len(results)
        ))
        return

    hpo_terms_by_id, genes_by_id, _ = get_mme_genes_phenotypes_for_results([incoming_patient])

    match_results = []
    all_emails = set()
    for result in new_matched_results:
        submission = result.submission
        individual = submission.individual
        project = individual.family.project

        result_text = """seqr ID {individual_id} from project {project_name} in family {family_id} inserted into
matchbox on {insertion_date}, with seqr link
{host}project/{project_guid}/family_page/{family_guid}/matchmaker_exchange""".replace('\n', ' ').format(
            individual_id=individual.individual_id, project_guid=project.guid, project_name=project.name,
            family_guid=individual.family.guid, family_id=individual.family.family_id,
            insertion_date=submission.created_date.strftime('%b %d, %Y'), host=BASE_URL)
        emails = [email.strip() for email in submission.contact_href.replace('mailto:', '').split(',')]
        send_emails = emails if len(emails) < 2 else [email for email in emails if email!= MME_DEFAULT_CONTACT_EMAIL]
        all_emails.update(send_emails)
        match_results.append((result_text, send_emails, submission.submission_id))
    match_results = sorted(match_results, key=lambda result_tuple: result_tuple[0])

    base_message = """Dear collaborators,

    matchbox found a match between a patient from {query_institution} and the following {number_of_results} case(s) 
    in matchbox. The following information was included with the query,

    genes: {incoming_query_genes}
    phenotypes: {incoming_query_phenotypes}
    contact: {incoming_query_contact_name}
    email: {incoming_query_contact_url}

    We sent back the following:

    """.format(
        query_institution=institution,
        number_of_results=len(results),
        incoming_query_genes=', '.join(sorted([gene['geneSymbol'] for gene in genes_by_id.values()])),
        incoming_query_phenotypes=', '.join(['{} ({})'.format(hpo_id, term) for hpo_id, term in hpo_terms_by_id.items()]),
        incoming_query_contact_url=contact_href,
        incoming_query_contact_name=incoming_patient['patient']['contact'].get('name', '(sorry I was not able to read the information given for name'),
    )

    message_template = """{base_message}{match_results}

    We sent this email alert to: {email_addresses_alert_sent_to}\n{footer}."""

    safe_post_to_slack(MME_SLACK_MATCH_NOTIFICATION_CHANNEL, message_template.format(
        base_message=base_message, match_results='\n'.join([result[0] for result in match_results]),
        email_addresses_alert_sent_to=', '.join(sorted(all_emails)), footer=MME_EMAIL_FOOTER
    ))

    for result_text, emails, submission_id in match_results:
        try:
            email_message = EmailMessage(
                subject='Received new MME match',
                body=message_template.format(
                    base_message=base_message, match_results=result_text,
                    email_addresses_alert_sent_to=', '.join(emails), footer=MME_EMAIL_FOOTER
                ),
                to=emails,
                from_email=MME_DEFAULT_CONTACT_EMAIL,
            )
            email_message.send()
        except Exception as e:
            logger.error(f'Unable to send notification email for incoming MME match with {submission_id}: {e}')


MME_EMAIL_FOOTER = """
Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
Our website can be found at https://seqr.populationgenomics.org.au/matchmaker/matchbox and our legal disclaimers can 
be found found at https://seqr.populationgenomics.org.au/matchmaker/disclaimer"""
