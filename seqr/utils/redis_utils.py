import json
import logging
import redis

from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from settings import REDIS_SERVICE_HOSTNAME, REDIS_SERVICE_PORT

logger = logging.getLogger(__name__)


def _redis_get(redis_client, cache_key):
    return redis_client.get(cache_key)


def safe_redis_get_json(cache_key, redis_get=_redis_get):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, port=REDIS_SERVICE_PORT, socket_connect_timeout=3)
        value = redis_get(redis_client, cache_key)
        if value:
            logger.info('Loaded {} from redis'.format(cache_key))
            return json.loads(value)
    except ValueError as e:
        logger.warning('Unable to fetch "{}" from redis:\t{}'.format(cache_key, str(e)))
    except Exception as e:
        logger.error('Unable to connect to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
    return None


def _redis_get_wildcard(redis_client, cache_key):
    keys = redis_client.keys(pattern=cache_key)
    if keys:
        return redis_client.get(keys[0])  # Return the first matching key's value
    return None


def safe_redis_get_wildcard_json(cache_key):
    return safe_redis_get_json(cache_key, redis_get=_redis_get_wildcard)


def safe_redis_set_json(cache_key, value, expire=None):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, port=REDIS_SERVICE_PORT, socket_connect_timeout=3)
        redis_client.set(cache_key, json.dumps(value, cls=DjangoJSONEncoderWithSets))
        if expire:
            redis_client.expire(cache_key, expire)
    except Exception as e:
        logger.error('Unable to write to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
