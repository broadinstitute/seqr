import json
import logging
import redis

from settings import REDIS_SERVICE_HOSTNAME

logger = logging.getLogger(__name__)


def safe_redis_get_json(cache_key):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        value = redis_client.get(cache_key)
        if value:
            logger.info('Loaded {} from redis'.format(cache_key))
            return json.loads(value)
    except ValueError as e:
        logger.warning('Unable to fetch "{}" from redis:\t{}'.format(cache_key, str(e)))
    except Exception as e:
        logger.error('Unable to connect to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
    return None


def safe_redis_set_json(cache_key, value):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        redis_client.set(cache_key, json.dumps(value))
    except Exception as e:
        logger.error('Unable to write to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
