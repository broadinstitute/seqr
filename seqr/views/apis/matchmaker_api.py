import json
import logging
import requests
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reference_data.models import HumanPhenotypeOntology

from seqr.models import Individual, MatchmakerResult
from seqr.model_utils import update_seqr_model
from seqr.utils.gene_utils import get_genes, get_gene_ids_for_gene_symbols
from seqr.utils.slack_utils import post_to_slack
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_model
from seqr.views.utils.permissions_utils import check_permissions

from settings import MME_HEADERS, MME_LOCAL_MATCH_URL, MME_EXTERNAL_MATCH_URL, SEQR_HOSTNAME_FOR_SLACK_POST,  \
    MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, MME_ADD_INDIVIDUAL_URL, MME_DELETE_INDIVIDUAL_URL

logger = logging.getLogger(__name__)


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
    return _search_individual_matches(individual, request.user)


def _search_individual_matches(individual, user):
    patient_data = individual.mme_submitted_data
    if not patient_data:
        return create_json_response(
            {}, status=404, reason='No matchmaker submission found for {}'.format(individual.individual_id),
        )

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
                last_modified_by=user,
            )
            new_results.append(result)
            saved_results[result['patient']['id']] = saved_result

    if new_results:
        _generate_slack_notification_for_seqr_match(individual, new_results)

    logger.info('Found {} matches for {} ({} new)'.format(len(results), individual.individual_id, len(new_results)))

    return _parse_mme_results(individual, saved_results.values())


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_mme_submission(request, individual_guid):
    """
    Create or update the submission for the given individual.
    """
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_permissions(project, request.user)

    submission_json = json.loads(request.body)

    submission_json.pop('individualGuid', {})
    phenotypes = submission_json.pop('phenotypes', [])
    gene_variants = submission_json.pop('geneVariants', [])
    if not phenotypes and not gene_variants:
        return create_json_response({}, status=400, reason='Genotypes or phentoypes are required')

    if not submission_json.get('patient', {}).get('id'):
        return create_json_response({}, status=400, reason='Patient id is required')

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

    submission_json['patient']['genomicFeatures'] = genomic_features
    submission_json['patient']['features'] = phenotypes

    response = requests.post(url=MME_ADD_INDIVIDUAL_URL, headers=MME_HEADERS, data=json.dumps(submission_json))

    if response.status_code not in (200, 409):
        try:
            response_json = response.json()
        except:
            response_json = {}
        return create_json_response(response_json, status=response.status_code, reason=response.content)

    submitted_date = datetime.now()
    individual.mme_submitted_data = submission_json
    individual.mme_submitted_date = submitted_date
    individual.mme_deleted_date = None
    individual.mme_deleted_by = None
    individual.save()

    # update the project contact information if anything new was added
    new_contact_names = set(submission_json['patient']['contact']['name'].split(',')) - set(project.mme_primary_data_owner.split(','))
    new_contact_urls = set(submission_json['patient']['contact']['href'].replace('mailto:', '').split(',')) - set(project.mme_contact_url.replace('mailto:', '').split(','))
    updates = {}
    if new_contact_names:
        updates['mme_primary_data_owner'] = '{},{}'.format(project.mme_primary_data_owner, ','.join(new_contact_names))
    if new_contact_urls:
        updates['mme_contact_url'] = '{},{}'.format(project.mme_contact_url, ','.join(new_contact_urls))
    if updates:
        update_seqr_model(project, **updates)

    # search for new matches
    return _search_individual_matches(individual, request.user)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_mme_submission(request, individual_guid):
    """
    Create or update the submission for the given individual.
    """
    individual = Individual.objects.get(guid=individual_guid)
    project = individual.family.project
    check_permissions(project, request.user)

    if individual.mme_deleted_date:
        return create_json_response(
            {}, status=402, reason='Matchmaker submission has already been deleted for {}'.format(individual.individual_id),
        )

    matchbox_id = individual.mme_submitted_data['patient']['id']
    response = requests.delete(url=MME_DELETE_INDIVIDUAL_URL, headers=MME_HEADERS, data=json.dumps({'id': matchbox_id}))

    if response.status_code != 200:
        try:
            response_json = response.json()
        except Exception:
            response_json = {}
        return create_json_response(response_json, status=response.status_code, reason=response.content)

    deleted_date = datetime.now()
    individual.mme_deleted_date = deleted_date
    individual.mme_deleted_by = request.user
    individual.save()

    return create_json_response({'individualsByGuid': {individual_guid: {'mmeDeletedDate': deleted_date}}})


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
            'mmeSubmittedData': parse_mme_patient(individual.mme_submitted_data, hpo_terms_by_id, gene_symbols_to_ids),
            'mmeSubmittedDate': individual.mme_submitted_date,
            'mmeDeletedDate': individual.mme_deleted_date,
        }},
        'genesById': genes_by_id,
    })


def _parse_mme_result(result, hpo_terms_by_id, gene_symbols_to_ids):
    parsed_result = parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids)
    parsed_result.update({
        'id': result['patient']['id'],
        'score': result['score']['patient'],
    })
    return parsed_result


def parse_mme_patient(result, hpo_terms_by_id, gene_symbols_to_ids):
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
                gene_variant.update({
                    'alt': gene_feature['variant'].get('alternateBases'),
                    'ref': gene_feature['variant'].get('referenceBases'),
                    'chrom': gene_feature['variant'].get('referenceName'),
                    'pos': gene_feature['variant'].get('start'),
                    'genomeVersion':  gene_feature['variant'].get('assembly'),
                })
            gene_variants.append(gene_variant)

    parsed_result = {
        'geneVariants': gene_variants,
        'phenotypes': phenotypes,
    }
    parsed_result.update(result)
    return parsed_result


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

    message = u"""
    A search from a seqr user from project {project} individual {individual_id} had the following new match(es):
    
    {matches}
    
    {host}/{project_guid}/family_page/{family_guid}/matchmaker_exchange
    """.format(
        project=individual.family.project.name, individual_id=individual.individual_id, matches='\n\n'.join(matches),
        host=SEQR_HOSTNAME_FOR_SLACK_POST, project_guid=individual.family.project.guid, family_guid=individual.family.guid,
    )

    post_to_slack(MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL, message)
