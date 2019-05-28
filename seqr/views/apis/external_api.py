import json
import logging
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Individual
from seqr.utils.slack_utils import post_to_slack
from seqr.views.apis.matchmaker_api import get_mme_genes_phenotypes
from seqr.views.utils.proxy_request_utils import proxy_request

from settings import MME_LOCAL_MATCH_URL, MME_MATCHBOX_PUBLIC_METRICS_URL, MME_SLACK_MATCH_NOTIFICATION_CHANNEL,\
    MME_SLACK_EVENT_NOTIFICATION_CHANNEL, SEQR_HOSTNAME_FOR_SLACK_POST

logger = logging.getLogger(__name__)


"""
ENDPOINTS IN THIS FILE ARE ACCESSED BY NON_SEQR USERS. BE CAREFUL WHEN EDITING NOT TO MAKE BREAKING CHANGES
"""


@csrf_exempt
def mme_metrics_proxy(request):
    """
    -This is a proxy URL for backend MME server as per MME spec.
    -Proxies public metrics endpoint

    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Metric JSON from matchbox
    NOTES:
    1. seqr login IS NOT required, since AUTH via toke in POST is handled by MME server, hence no
    decorator @login_required. This is a PUBLIC endpoint

    """
    return proxy_request(request, MME_MATCHBOX_PUBLIC_METRICS_URL)


@csrf_exempt
def mme_match_proxy(request):
    """
    -This is a proxy URL for backend MME server as per MME spec.
    -Looks for matches for the given individual ONLY in the local MME DB.
    -Expects a single patient (as per MME spec) in the POST

    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results (as per MME spec), returns raw results from MME Server
    NOTES:
    1. login is not required, since AUTH is handled by MME server, hence missing
    decorator @login_required

    """
    query_patient_data = ''
    for line in request.readlines():
        query_patient_data = query_patient_data + ' ' + line
    response = proxy_request(request, MME_LOCAL_MATCH_URL, data=query_patient_data)
    if response.status_code == 200:
        try:
            _generate_notification_for_incoming_match(response, request, query_patient_data)
        except Exception:
            logger.error('Unable to create slack notification for incoming MME match request')
    return response


def _generate_notification_for_incoming_match(response_from_matchbox, incoming_request, incoming_patient):
    """
    Generate a SLACK notifcation to say that a VALID match request came in and the following
    results were sent back. If Slack is not supported, a message is not sent, but details persisted.

    Args:
        response_from_matchbox (python requests object): contains the response from matchbox
        incoming_request (Django request object): The request that came into the view
        incoming_patient (JSON): The query patient JSON structure from outside MME node that was matched with
    """
    results_from_matchbox = json.loads(response_from_matchbox.content)['results']
    incoming_patient = json.loads(incoming_patient.strip())
    incoming_patient_id = incoming_patient['patient']['id']

    logger.info('{} MME matches found for patient {} from {}'.format(
        len(results_from_matchbox), incoming_patient_id, incoming_request.get_host())
    )

    institution = incoming_patient['patient']['contact'].get('institution', '(institution name not given)')
    contact_href = incoming_patient['patient']['contact'].get('href', '(sorry I was not able to read the information given for URL)')
    if len(results_from_matchbox) > 0:
        hpo_terms_by_id, genes_by_id, _ = get_mme_genes_phenotypes([incoming_patient])

        match_results = []
        emails = set()
        for result in results_from_matchbox:
            individual = Individual.objects.filter(mme_submitted_data__patient__id=result['patient']['id']).first()
            project = individual.family.project

            result_text = u'seqr ID {individual_id} from project {project_name} in family {family_id} ' \
                          u'inserted into matchbox on {insertion_date}, with seqr link ' \
                          u'{host}/{project_guid}/family_page/{family_guid}/matchmaker_exchange'.format(
                individual_id=individual.individual_id, project_guid=project.guid, project_name=project.name,
                family_guid=individual.family.guid, family_id=individual.family.family_id,
                insertion_date=individual.mme_submitted_date.strftime('%b %d, %Y'), host=SEQR_HOSTNAME_FOR_SLACK_POST)
            match_results.append(result_text)
            emails.update([i for i in project.mme_contact_url.replace('mailto:', '').split(',')])

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
            number_of_results=len(results_from_matchbox),
            incoming_query_genes=', '.join(sorted([gene['geneSymbol'] for gene in genes_by_id.values()])),
            incoming_query_phenotypes=', '.join(['{} ({})'.format(hpo_id, term) for hpo_id, term in hpo_terms_by_id.items()]),
            incoming_query_contact_url=contact_href,
            incoming_query_contact_name=incoming_patient['patient']['contact'].get('name', '(sorry I was not able to read the information given for name'),
            match_results='\n'.join(match_results),
            email_addresses_alert_sent_to=', '.join(emails),
        )

        post_to_slack(MME_SLACK_MATCH_NOTIFICATION_CHANNEL, message)
    else:
        message = """Dear collaborators,
        
        This match request came in from {institution} today ({today}). The contact information given was: {contact}.
        
        We didn't find any individuals in matchbox that matched that query well, *so no results were sent back*.
        """.format(institution=institution, today=datetime.now().strftime('%b %d, %Y'), contact=contact_href)

        post_to_slack(MME_SLACK_EVENT_NOTIFICATION_CHANNEL, message)
