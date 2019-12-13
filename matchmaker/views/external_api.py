import json
import logging
from datetime import datetime
from django.core.mail.message import EmailMessage
from django.views.decorators.csrf import csrf_exempt

from matchmaker.models import MatchmakerSubmission
from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_results, get_mme_metrics, get_mme_matches

from seqr.utils.communication_utils import post_to_slack
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.proxy_request_utils import proxy_request

from settings import MME_ACCEPT_HEADER, MME_NODES, MME_SLACK_MATCH_NOTIFICATION_CHANNEL,\
    MME_SLACK_EVENT_NOTIFICATION_CHANNEL, MME_DEFAULT_CONTACT_EMAIL, BASE_URL

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

        return view_func(request, originating_node, *args, **kwargs)
    return _wrapped_view


@authenticate_mme_request
@csrf_exempt
def mme_metrics_proxy(request, originating_node):
    """
    -Proxies public metrics endpoint
    Returns:
        Metric JSON from matchbox
    """
    logger.info('Received MME metrics request from {}'.format(originating_node['name']))
    return create_json_response({'metrics': get_mme_metrics()})


@authenticate_mme_request
@csrf_exempt
def mme_match_proxy(request, originating_node):
    """
    -Looks for matches for the given individual ONLY in the local MME DB.
    -Expects a single patient (as per MME spec) in the POST

    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results (as per MME spec), returns raw results from MME Server
    """
    logger.info('Received MME match request from {}'.format(originating_node['name']))

    try:
        query_patient_data = json.loads(request.body)
        _validate_patient_data(query_patient_data)
    except Exception as e:
        return create_json_response({'message': e.message}, status=400)

    results, incoming_query = get_mme_matches(
        patient_data=query_patient_data, origin_request_host=originating_node['name'],
    )

    try:
        _generate_notification_for_incoming_match(results, request, query_patient_data)
    except Exception as e:
        logger.error('Unable to create notification for incoming MME match request: {}'.format(e.message))

    return create_json_response({
        'results': sorted(results, key=lambda result: result['score']['patient'], reverse=True),
        '_disclaimer': MME_DISCLAIMER,
    })


def _validate_patient_data(query_patient_data):
    patient_data = query_patient_data.get('patient')
    if not patient_data:
        raise ValueError('"patient" is required')
    if not patient_data.get('id'):
        raise ValueError('"id" is required')
    if not patient_data.get('contact'):
        raise ValueError('"contact" is required')
    if not (patient_data.get('features') or patient_data.get('genomicFeatures')):
        raise ValueError('"features" or "genomicFeatures" are required')


def _generate_notification_for_incoming_match(results, incoming_request, incoming_patient):
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
        len(results), incoming_patient_id, incoming_request.get_host())
    )

    institution = incoming_patient['patient']['contact'].get('institution', '(institution name not given)')
    contact_href = incoming_patient['patient']['contact'].get('href', '(sorry I was not able to read the information given for URL)')
    if len(results) > 0:
        hpo_terms_by_id, genes_by_id, _ = get_mme_genes_phenotypes_for_results([incoming_patient])

        match_results = []
        emails = set()
        for result in results:
            submission = MatchmakerSubmission.objects.get(submission_id=result['patient']['id'])
            individual = submission.individual
            project = individual.family.project

            result_text = u'seqr ID {individual_id} from project {project_name} in family {family_id} ' \
                          u'inserted into matchbox on {insertion_date}, with seqr link ' \
                          u'{host}project/{project_guid}/family_page/{family_guid}/matchmaker_exchange'.format(
                individual_id=individual.individual_id, project_guid=project.guid, project_name=project.name,
                family_guid=individual.family.guid, family_id=individual.family.family_id,
                insertion_date=submission.created_date.strftime('%b %d, %Y'), host=BASE_URL)
            match_results.append(result_text)
            emails.update([i.strip() for i in project.mme_contact_url.replace('mailto:', '').split(',')])
        emails = [email for email in emails if email != MME_DEFAULT_CONTACT_EMAIL]

        message = u"""Dear collaborators,

        matchbox found a match between a patient from {query_institution} and the following {number_of_results} case(s) 
        in matchbox. The following information was included with the query,

        genes: {incoming_query_genes}
        phenotypes: {incoming_query_phenotypes}
        contact: {incoming_query_contact_name}
        email: {incoming_query_contact_url}

        We sent back:

        {match_results}

        We sent this email alert to: {email_addresses_alert_sent_to}

        Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
        Our website can be found at https://seqr.broadinstitute.org/matchmaker/matchbox and our legal disclaimers can 
        be found found at https://seqr.broadinstitute.org/matchmaker/disclaimer.""".format(
            query_institution=institution,
            number_of_results=len(results),
            incoming_query_genes=', '.join(sorted([gene['geneSymbol'] for gene in genes_by_id.values()])),
            incoming_query_phenotypes=', '.join(['{} ({})'.format(hpo_id, term) for hpo_id, term in hpo_terms_by_id.items()]),
            incoming_query_contact_url=contact_href,
            incoming_query_contact_name=incoming_patient['patient']['contact'].get('name', '(sorry I was not able to read the information given for name'),
            match_results='\n'.join(match_results),
            email_addresses_alert_sent_to=', '.join(emails),
        )

        post_to_slack(MME_SLACK_MATCH_NOTIFICATION_CHANNEL, message)
        #  TODO re-enable MME email
        # email_message = EmailMessage(
        #     subject='Received new MME match',
        #     body=message,
        #     to=emails,
        #     from_email=MME_DEFAULT_CONTACT_EMAIL,
        # )
        # email_message.send()
    else:
        message = """Dear collaborators,
        
        This match request came in from {institution} today ({today}). The contact information given was: {contact}.
        
        We didn't find any individuals in matchbox that matched that query well, *so no results were sent back*.
        """.format(institution=institution, today=datetime.now().strftime('%b %d, %Y'), contact=contact_href)

        post_to_slack(MME_SLACK_EVENT_NOTIFICATION_CHANNEL, message)


MME_DISCLAIMER = """The data in Matchmaker Exchange is provided for research use only. Broad Institute provides the data
in Matchmaker Exchange 'as is'. Broad Institute makes no representations or warranties of any kind concerning the data,
express or implied, including without limitation, warranties of merchantability, fitness for a particular purpose,
noninfringement, or the absence of latent or other defects, whether or not discoverable. Broad will not be liable to the
user or any third parties claiming through user, for any loss or damage suffered through the use of Matchmaker Exchange.
In no event shall Broad Institute or its respective directors, officers, employees, affiliated investigators and
affiliates be liable for indirect, special, incidental or consequential damages or injury to property and lost profits,
regardless of whether the foregoing have been advised, shall have other reason to know, or in fact shall know of the
possibility of the foregoing. Prior to using Broad Institute data in a publication, the user will contact the owner of
the matching dataset to assess the integrity of the match. If the match is validated, the user will offer appropriate
recognition of the data owner's contribution, in accordance with academic standards and custom. Proper acknowledgment
shall be made for the contributions of a party to such results being published or otherwise disclosed, which may include
co-authorship. If Broad Institute contributes to the results being published, the authors must acknowledge Broad
Institute using the following wording: 'This study makes use of data shared through the Broad Institute matchbox
repository. Funding for the Broad Institute was provided in part by National Institutes of Health grant UM1 HG008900 to
Daniel MacArthur and Heidi Rehm.' User will not attempt to use the data or Matchmaker Exchange to establish the
individual identities of any of the subjects from whom the data were obtained. This applies to matches made within Broad
Institute or with any other database included in the Matchmaker Exchange.""".replace('\n', ' ')
