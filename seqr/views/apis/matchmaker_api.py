import json
import logging
import requests
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reference_data.models import HumanPhenotypeOntology, GENOME_VERSION_CHOICES

from seqr.models import Individual, MatchmakerResult
from seqr.utils.gene_utils import get_genes, get_gene_ids_for_gene_symbols
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model
from seqr.views.utils.permissions_utils import check_permissions

from settings import MME_NODE_ADMIN_TOKEN, MME_NODE_ACCEPT_HEADER, MME_CONTENT_TYPE_HEADER, MME_LOCAL_MATCH_URL, \
    MME_EXTERNAL_MATCH_URL

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
    return _parse_mme_results(individual_guid, results)


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
            {}, status_code=404, reason='No matchmaker submission found for {}'.format(individual.individual_id),
        )

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

    saved_results = {
        result.result_data['patient']['id']: result for result in MatchmakerResult.objects.filter(individual=individual)
    }

    new_result_count = 0
    for result in results:
        saved_result = saved_results.get(result['patient']['id'])
        if not saved_result:
            saved_result = MatchmakerResult.objects.create(
                individual=individual,
                result_data=result,
                last_modified_by=request.user,
            )
            new_result_count += 1
            saved_results[result['patient']['id']] = saved_result

    # TODO post to slack

    logger.info('Found {} matches for {} ({} new)'.format(len(results), individual.individual_id, new_result_count))

    return _parse_mme_results(individual_guid, saved_results.values())


def _parse_mme_results(individual_guid, saved_results):
    hpo_ids = set()
    genes = set()
    results = []
    for result_model in saved_results:
        result = result_model.result_data
        result['matchStatus'] = _get_json_for_model(result_model)
        results.append(result)

        hpo_ids.update({feature['id'] for feature in result['patient'].get('features', []) if feature.get('id')})
        genes.update({gene_feature['gene']['id'] for gene_feature in result['patient'].get('genomicFeatures', [])})

    gene_ids = {gene for gene in genes if gene.startswith('ENSG')}
    gene_symols = {gene for gene in genes if not gene.startswith('ENSG')}
    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symols)
    gene_ids.update({new_gene_ids[0] for new_gene_ids in gene_symbols_to_ids.values()})
    genes_by_id = get_genes(gene_ids)

    hpo_terms_by_id = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=hpo_ids)}

    parsed_results = [_parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids) for result in results]
    return create_json_response({
        'individualsByGuid': {individual_guid: {'mmeResults': parsed_results}},
        'genesById': genes_by_id,
    })


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids):
    phenotypes = [feature for feature in result['patient'].get('features', [])]
    for feature in phenotypes:
        feature['name'] = hpo_terms_by_id.get(feature['id'])

    gene_variants = defaultdict(list)
    for gene_feature in result['patient'].get('genomicFeatures', []):
        gene_id = gene_feature['gene']['id']
        if not gene_id.startswith('ENSG'):
            gene_ids = gene_symbols_to_ids.get(gene_feature['gene']['id'])
            gene_id = gene_ids[0] if gene_ids else None

        if gene_id:
            if gene_feature.get('variant'):
                assembly = gene_feature['variant'].get('assembly')
                gene_variants[gene_id].append({
                    'alt': gene_feature['variant'].get('alternateBases'),
                    'ref': gene_feature['variant'].get('referenceBases'),
                    'chrom': gene_feature['variant'].get('referenceName'),
                    'pos': gene_feature['variant'].get('start'),
                    'genomeVersion': GENOME_VERSION_LOOKUP.get(assembly, assembly),
                })
            else:
                # Ensures key is present in defaultdict
                gene_variants[gene_id]
    patient = {
        k: result['patient'].get(k) for k in ['inheritanceMode', 'sex', 'contact', 'ageOfOnset', 'label', 'species']
    }
    return {
        'id': result['patient']['id'],
        'score': result['score']['patient'],
        'geneVariants': dict(gene_variants),
        'phenotypes': phenotypes,
        'patient': patient,
        'matchStatus': result['matchStatus'],
    }
