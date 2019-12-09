import logging
import pymongo
import os
import json

from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError

from matchmaker.models import MatchmakerIncomingQuery, MatchmakerResult, MatchmakerSubmission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer MME data to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--skip-match-result-validation', action='store_true')

    def handle(self, *args, **options):
        MONGO_SERVICE_HOSTNAME = os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost')
        _client = pymongo.MongoClient(MONGO_SERVICE_HOSTNAME, 27017)
        external_queries_collection = _client['mme_primary']['externalMatchQuery']
        # transfer_mme_queries(external_queries_collection)
        set_mme_query_results(external_queries_collection, skip_validation=options['skip_match_result_validation'])


def _get_query_guid(query):
    return 'MIQ:{}'.format(query['_id'])[:30]


def _get_result_guid(result):
    patient_id = result['result']['patient']['_id'][:20]
    query_guid = str(result['query']['_id'])
    return 'MR:{}_{}'.format(patient_id, query_guid[len(query_guid)-(26-len(patient_id)):])


def transfer_mme_queries(external_queries_collection):
    external_queries = external_queries_collection.find(
        {}, {"timeStamp": 1, "institution": 1, "requestOriginHostname": 1, "incomingQuery._id": 1}
    )
    logger.info('Transferring {} queries'.format(external_queries.count()))

    new_models = [
        MatchmakerIncomingQuery(
            guid=_get_query_guid(query),
            created_date=query['timeStamp'],
            last_modified_date=query['timeStamp'],
            institution=query.get('institution') or query['requestOriginHostname'],
            patient_id=query.get('incomingQuery', {}).get('_id'),
        )
        for query in external_queries
    ]
    MatchmakerIncomingQuery.objects.bulk_create(new_models)
    logger.info('Successfully copied {} queries'.format(len(new_models)))


def set_mme_query_results(external_queries_collection, skip_validation=False):
    matched_queries = external_queries_collection.find(
        {"matchFound": True}, {"results": 1, "incomingQuery._id": 1, "timeStamp": 1}
    )
    matched_queries = sorted(matched_queries, key=lambda query: query["timeStamp"], reverse=True)
    logger.info('Found {} matched queries'.format(len(matched_queries)))

    results_by_patient_id = defaultdict(dict)
    for query in matched_queries:
        query['guid'] = _get_query_guid(query)
        query_id = query['incomingQuery']['_id']
        for result in query.pop('results'):
            if result['patient']['_id'] != query_id:
                results_by_patient_id[result['patient']['_id']][query_id] = {'result': result, 'query': query}

    logger.info('Found {} distinct mongo result patients'.format(len(results_by_patient_id)))

    existing_results_by_patient_id = defaultdict(list)
    for result in MatchmakerResult.objects.all().prefetch_related('submission'):
        existing_results_by_patient_id[result.result_data['patient']['id']].append(result)

    logger.info('Found {} distinct seqr result patients'.format(len(existing_results_by_patient_id)))

    existing_results = {}
    new_results = []
    for patient_id, results in results_by_patient_id.items():
        existing_query_ids = set()
        for result in existing_results_by_patient_id[patient_id]:
            query_id = result.submission.submission_id
            mongo_result = results.get(query_id)
            if not mongo_result:
                continue
            if not skip_validation:
                _validate_matched_existing_result(result, mongo_result)
            existing_query_ids.add(query_id)
            existing_results[result] = mongo_result['query']
        for query_id, result in results.items():
            if query_id not in existing_query_ids:
                new_results.append(result)

    logger.info('Found matches for {} existing results; found {} new results'.format(len(existing_results), len(new_results)))

    all_query_ids = {result['query']['guid'] for result in new_results}
    all_query_ids.update({query['guid'] for query in existing_results.values()})
    queries_by_guid = {query.guid: query for query in MatchmakerIncomingQuery.objects.filter(guid__in=all_query_ids)}
    submissions_by_id = {submission.submission_id: submission for submission in MatchmakerSubmission.objects.all()}

    if not skip_validation:
        missing_submission_queries = {
            result['query']['incomingQuery']['_id']: queries_by_guid[result['query']['guid']].institution
            for result in new_results if 'broad' in queries_by_guid[result['query']['guid']].institution.lower()
                                         and result['query']['incomingQuery']['_id'] not in submissions_by_id
        }
        if missing_submission_queries:
            logger.warn('Broad queries missing a submission: {}'.format(', '.join(['{} ({})'.format(
                patient_id, institution) for patient_id, institution in missing_submission_queries.items()])))

    for result, query in existing_results.items():
        result.originating_query = queries_by_guid[query['guid']]
        result.save()
    logger.info('Successfully updated queries for {} results'.format(len(existing_results)))

    new_models = [
        MatchmakerResult(
            originating_query=queries_by_guid[result['query']['guid']],
            submission=submissions_by_id.get(result['query']['incomingQuery']['_id']),
            created_date=result['query']['timeStamp'],
            guid=_get_result_guid(result),
            result_data=_update_id_field(result['result']),
            match_removed=True,
        )
        for result in new_results
    ]
    MatchmakerResult.objects.bulk_create(new_models)
    logger.info('Successfully copied {} queries'.format(len(new_models)))


def _update_id_field(result):
    result['patient']['id'] = result['patient'].pop('_id')
    for feature in result['patient']['features']:
        feature['id'] = feature.pop('_id')
    return result


def _validate_matched_existing_result(result, mongo_result):
    diff = {
        k: v for k, v in result.result_data['patient'].items()
        if v and v != mongo_result['result']['patient']['_id' if k == 'id' else k]
    }
    if 'genomicFeatures' in diff:
        diff_features = []
        expected_features = mongo_result['result']['patient']['genomicFeatures']
        for i, feature in enumerate(diff['genomicFeatures']):
            diff_feature = {
                k: v for k, v in feature.items() if k in {
                'alternateBases', 'referenceBases', 'referenceName', 'start', 'assembly',
            } and v != expected_features[i][k]}
            if diff_feature:
                diff_features.push(diff_feature)
        if diff_features:
            diff['genomicFeatures'] = diff_features
        else:
            del diff['genomicFeatures']
    if 'features' in diff:
        diff_features = []
        expected_features = mongo_result['result']['patient']['features']
        for i, feature in enumerate(diff['features']):
            diff_feature = {
                k: v for k, v in feature.items() if v and v != expected_features[i]['_id' if k == 'id' else k]
            }
            if diff_feature:
                diff_features.push(diff_feature)
        if diff_features:
            diff['features'] = diff_features
        else:
            del diff['features']
    if diff:
        raise CommandError('Mismatched mongo and seqr result]\nseqr: {}\nmongo: {}'.format(
            json.dumps(diff), json.dumps({k: mongo_result['result']['patient'].get(k) for k in diff.keys()}),
        ))


