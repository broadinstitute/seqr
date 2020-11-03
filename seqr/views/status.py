from django.db import connections
import logging
import redis
import requests

from settings import SEQR_VERSION, KIBANA_SERVER, REDIS_SERVICE_HOSTNAME, DATABASES
from seqr.utils.elasticsearch.utils import get_es_client
from seqr.views.utils.json_utils import create_json_response

logger = logging.getLogger(__name__)


def status_view(request):
    """Status endpoint for monitoring app availability."""
    dependent_services_ok = True

    # Test database connection
    for db_connection_key in DATABASES.keys():
        try:
            connections[db_connection_key].cursor()
        except Exception as e:
            dependent_services_ok = False
            logger.error('Unable to connect to database "{}": {}'.format(db_connection_key, e))

    # Test redis connection
    try:
        redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3).ping()
    except Exception as e:
        dependent_services_ok = False
        logger.error('Unable to connect to redis: {}'.format(str(e)))

    # Test elasticsearch connection
    try:
        if not get_es_client(timeout=3, max_retries=0).ping():
            raise ValueError('No response from elasticsearch ping')
    except Exception as e:
        dependent_services_ok = False
        logger.error('Unable to connect to elasticsearch: {}'.format(str(e)))

    # Test kibana connection
    try:
        requests.head('http://{}/status'.format(KIBANA_SERVER), timeout=3).raise_for_status()
    except Exception as e:
        dependent_services_ok = False
        logger.error('Unable to connect to kibana: {}'.format(str(e)))


    return create_json_response(
        {'version': SEQR_VERSION, 'dependent_services_ok': dependent_services_ok},
        status= 200 if dependent_services_ok else 400
    )
