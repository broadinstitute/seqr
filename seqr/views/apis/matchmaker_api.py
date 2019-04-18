import json
import logging
import pymongo
import requests
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from reference_data.models import HumanPhenotypeOntology

from seqr.models import Individual
from seqr.utils.gene_utils import get_genes, get_gene_ids_for_gene_symbols
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import check_permissions

from settings import MME_NODE_ADMIN_TOKEN, MME_NODE_ACCEPT_HEADER, MME_CONTENT_TYPE_HEADER, MME_LOCAL_MATCH_URL, \
    MME_EXTERNAL_MATCH_URL, SEQR_ID_TO_MME_ID_MAP, MME_SEARCH_RESULT_ANALYSIS_STATE

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_individual_matches(request, individual_guid):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """

    individul = Individual.objects.get(guid=individual_guid)
    project = individul.family.project
    check_permissions(project, request.user)

    # TODO use MME API not direct access to db
    submission = SEQR_ID_TO_MME_ID_MAP.find_one(
        {'project_id': project.deprecated_project_id, 'seqr_id': individul.individual_id},
        sort=[('insertion_date', pymongo.DESCENDING)]
    )
    if not submission:
        create_json_response(
            {}, status_code=404, reason='No matchmaker submission found for {}'.format(individul.individual_id),
        )

    patient_data = submission['submitted_data']

    headers = {
        'X-Auth-Token': MME_NODE_ADMIN_TOKEN,
        'Accept': MME_NODE_ACCEPT_HEADER,
        'Content-Type': MME_CONTENT_TYPE_HEADER
    }

    local_result = requests.post(url=MME_LOCAL_MATCH_URL, headers=headers, data=json.dumps(patient_data))
    if local_result.status_code != 200:
        create_json_response(local_result.json(), status_code=local_result.status_code, reason='Error in local match')

    external_result = requests.post(url=MME_EXTERNAL_MATCH_URL, headers=headers, data=json.dumps(patient_data))
    if external_result.status_code != 200:
        create_json_response(external_result.json(), status_code=external_result.status_code, reason='Error in external match')

    results = local_result.json()['results'] + external_result.json()['results']

    # TODO use postgres not mongo
    results_analysis_state = {
        detail['result_id']: detail for detail in MME_SEARCH_RESULT_ANALYSIS_STATE.find(
            {'seqr_project_id': project.deprecated_project_id, 'id_of_indiv_searched_with': individul.individual_id}
        )}

    hpo_ids = {feature['id'] for feature in patient_data['patient'].get('features', []) if feature.get('id')}
    genes = set()

    new_result_count = 0
    for result in results:
        # Get analysis state for result
        result_analysis_state = results_analysis_state.get(result['patient']['id'])
        if not result_analysis_state:
            # TODO use postgres not mongo
            result_analysis_state = {
                "id_of_indiv_searched_with": individul.individual_id,
                "content_of_indiv_searched_with": patient_data,
                "content_of_result": result,
                "result_id": id,
                "we_contacted_host": False,
                "host_contacted_us": False,
                "seen_on": str(timezone.now()),
                "deemed_irrelevant": False,
                "comments": "",
                "seqr_project_id": project.deprecated_project_id,
                "flag_for_analysis": False,
                "username_of_last_event_initiator": request.user.username
            }
            MME_SEARCH_RESULT_ANALYSIS_STATE.insert(result_analysis_state, manipulate=False)
            new_result_count += 1
        result_analysis_state.pop('_id', None)
        result['analysis_state'] = result_analysis_state

        hpo_ids.update({feature['id'] for feature in result['patient'].get('features', []) if feature.get('id')})
        genes.update({gene_feature['gene']['id'] for gene_feature in result['patient'].get('genomicFeatures', [])})

    # TODO post to slack

    logger.info('Found {} matches for {} ({} new)'.format(len(results), individul.individual_id, new_result_count))

    gene_ids = {gene for gene in genes if gene.startswith('ENSG')}
    gene_symols = {gene for gene in genes if not gene.startswith('ENSG')}
    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symols)
    gene_ids.update({new_gene_ids[0] for new_gene_ids in gene_symbols_to_ids.values()})
    genes_by_id = get_genes(gene_ids)

    hpo_terms_by_id = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=hpo_ids)}

    return create_json_response({
        'mmeResults': [_parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids) for result in results],
        'genesById': genes_by_id,
    })


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids):
    phenotypes = [feature for feature in result['patient'].get('features', []) if feature.get('observed') != 'no']
    for feature in phenotypes:
        feature['name'] = hpo_terms_by_id.get(feature['id'])

    gene_ids = set()
    for gene in result['patient'].get('genomicFeatures', []):
        if gene['gene']['id'].startswith('ENSG'):
            gene_ids.add(gene['gene']['id'])
        else:
            gene_id = gene_symbols_to_ids.get(gene['gene']['id'])
            if gene_id:
                gene_ids.add(gene_id[0])
    return {
        'id': result['patient']['id'],
        'score': result['score']['patient'],
        'hostContacted': result['analysis_state']['host_contacted_us'],
        'weContacted': result['analysis_state']['we_contacted_host'],
        'comments': result['analysis_state']['comments'],
        'geneIds': list(gene_ids),
        'phenotypes': phenotypes,
    }
