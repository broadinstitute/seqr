import json
import logging
import requests
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reference_data.models import HumanPhenotypeOntology, GENOME_VERSION_CHOICES

from seqr.models import Individual, MatchmakerResult
from seqr.utils.gene_utils import get_genes, get_gene_ids_for_gene_symbols
from seqr.utils.slack_utils import post_to_slack
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model
from seqr.views.utils.permissions_utils import check_permissions

from settings import MME_NODE_ADMIN_TOKEN, MME_NODE_ACCEPT_HEADER, MME_CONTENT_TYPE_HEADER, MME_LOCAL_MATCH_URL, \
    MME_EXTERNAL_MATCH_URL, MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, SEQR_HOSTNAME_FOR_SLACK_POST, MONARCH_MATCH_URL

logger = logging.getLogger(__name__)

GENOME_VERSION_LOOKUP = {}
for v, k in GENOME_VERSION_CHOICES:
    GENOME_VERSION_LOOKUP[k] = v


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_individual_mme_matches(request, individual_guid):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_permissions(project, request.user)

    results = MatchmakerResult.objects.filter(individual=individual)
    return _parse_mme_results(individual, results)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def search_individual_mme_matches(request, individual_guid):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        project_id,indiv_id and POST all data in POST under key "patient_data"
    Returns:
        Status code and results
    """

    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_permissions(project, request.user)

    patient_data = individual.mme_submitted_data
    if not patient_data:
        create_json_response(
            {}, status=404, reason='No matchmaker submission found for {}'.format(individual.individual_id),
        )

    headers = {
        'X-Auth-Token': MME_NODE_ADMIN_TOKEN,
        'Accept': MME_NODE_ACCEPT_HEADER,
        'Content-Type': MME_CONTENT_TYPE_HEADER
    }

    local_result = requests.post(url=MME_LOCAL_MATCH_URL, headers=headers, data=json.dumps(patient_data))
    if local_result.status_code != 200:
        create_json_response(local_result.json(), status=local_result.status_code, reason='Error in local match')

    external_result = requests.post(url=MME_EXTERNAL_MATCH_URL, headers=headers, data=json.dumps(patient_data))
    if external_result.status_code != 200:
        create_json_response(external_result.json(), status=external_result.status_code, reason='Error in external match')

    results = local_result.json()['results'] + external_result.json()['results']

    saved_results = {
        result.result_data['patient']['id']: result for result in MatchmakerResult.objects.filter(individual=individual)
    }

    new_results = []
    for result in results:
        saved_result = saved_results.get(result['patient']['id'])
        if not saved_result:
            saved_result = MatchmakerResult.objects.create(
                individual=individual,
                result_data=result,
                last_modified_by=request.user,
            )
            new_results.append(result)
            saved_results[result['patient']['id']] = saved_result

    if new_results:
        _generate_slack_notification_for_seqr_match(individual, new_results)

    logger.info('Found {} matches for {} ({} new)'.format(len(results), individual.individual_id, len(new_results)))

    return _parse_mme_results(individual, saved_results.values())


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def search_individual_monarch_matches(request, individual_guid):
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_permissions(project, request.user)

    patient_data = individual.mme_submitted_data
    if not patient_data:
        create_json_response(
            {}, status=404, reason='No matchmaker submission found for {}'.format(individual.individual_id),
        )

    headers = {
        'Accept': MME_NODE_ACCEPT_HEADER,
        'Content-Type': MME_CONTENT_TYPE_HEADER
    }
    response = requests.post(url=MONARCH_MATCH_URL, headers=headers, data=json.dumps(patient_data))
    results = response.json().get('results', [])

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes(results)

    parsed_results = [_parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids) for result in results]
    return create_json_response({
        'monarchResults': parsed_results,
        'genesById': genes_by_id,
    })


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
    project = result.individual.family.project
    check_permissions(project, request.user)

    request_json = json.loads(request.body)
    update_model_from_json(result, request_json, allow_unknown_keys=True)

    return create_json_response({
        'mmeResultsByGuid': {matchmaker_result_guid: {'matchStatus': _get_json_for_model(result)}},
    })


def get_mme_genes_phenotypes(results):
    hpo_ids = set()
    genes = set()
    for result in results:
        hpo_ids.update({feature['id'] for feature in result['patient'].get('features', []) if feature.get('id')})
        genes.update({gene_feature['gene']['id'] for gene_feature in result['patient'].get('genomicFeatures', [])})

    gene_ids = {gene for gene in genes if gene.startswith('ENSG')}
    gene_symols = {gene for gene in genes if not gene.startswith('ENSG')}
    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symols)
    gene_ids.update({new_gene_ids[0] for new_gene_ids in gene_symbols_to_ids.values()})
    genes_by_id = get_genes(gene_ids)

    hpo_terms_by_id = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=hpo_ids)}

    return hpo_terms_by_id, genes_by_id, gene_symbols_to_ids


def _parse_mme_results(individual, saved_results):
    results = []
    for result_model in saved_results:
        result = result_model.result_data
        result['matchStatus'] = _get_json_for_model(result_model)
        results.append(result)

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes(results + [individual.mme_submitted_data])

    parsed_results = [_parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids) for result in results]
    parsed_results_gy_guid = {result['matchStatus']['matchmakerResultGuid']: result for result in parsed_results}
    return create_json_response({
        'mmeResultsByGuid': parsed_results_gy_guid,
        'individualsByGuid': {individual.guid: {
            'mmeResultGuids': parsed_results_gy_guid.keys(),
            'mmeSubmittedData': _parse_mme_patient(individual.mme_submitted_data, hpo_terms_by_id, gene_symbols_to_ids),
        }},
        'genesById': genes_by_id,
    })


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids):
    parsed_result = _parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids)
    parsed_result.update({
        'id': result['patient']['id'],
        'score': result['score']['patient'],
        'matchStatus': result['matchStatus'],
    })
    return parsed_result


def _parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids):
    phenotypes = [feature for feature in result['patient'].get('features', [])]
    for feature in phenotypes:
        feature['label'] = hpo_terms_by_id.get(feature['id'])

    gene_variants = []
    for gene_feature in result['patient'].get('genomicFeatures', []):
        gene_id = gene_feature['gene']['id']
        if not gene_id.startswith('ENSG'):
            gene_ids = gene_symbols_to_ids.get(gene_feature['gene']['id'])
            gene_id = gene_ids[0] if gene_ids else None

        gene_variant = {'geneId': gene_id}
        if gene_id:
            if gene_feature.get('variant'):
                assembly = gene_feature['variant'].get('assembly')
                gene_variant.update({
                    'alt': gene_feature['variant'].get('alternateBases'),
                    'ref': gene_feature['variant'].get('referenceBases'),
                    'chrom': gene_feature['variant'].get('referenceName'),
                    'pos': gene_feature['variant'].get('start'),
                    'genomeVersion': GENOME_VERSION_LOOKUP.get(assembly, assembly),
                })
            gene_variants.append(gene_variant)
    patient = {
        k: result['patient'].get(k) for k in ['inheritanceMode', 'sex', 'contact', 'ageOfOnset', 'label', 'species']
    }
    return {
        'geneVariants': gene_variants,
        'phenotypes': phenotypes,
        'patient': patient,
    }


def _generate_slack_notification_for_seqr_match(individual, results):
    """
    Generate a SLACK notifcation to say that a match happened initiated from a seqr user.
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

    message = """
    A search from a seqr user from project {project} individual {individual_id} had the following new match(es):
    
    {matches}
    
    {host}/project/{project_guid}/family_page/{family_guid}/matchmaker_exchange
    """.format(
        project=individual.family.project.name, individual_id=individual.individual_id, matches='\n\n'.join(matches),
        host=SEQR_HOSTNAME_FOR_SLACK_POST, project_guid=individual.family.project.guid, family_guid=individual.family.guid,
    )

    post_to_slack(MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, message)
