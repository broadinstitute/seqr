import json
import logging
import redis

from settings import REDIS_SERVICE_HOSTNAME, REDIS_SERVICE_PORT, DEPLOYMENT_TYPE

logger = logging.getLogger(__name__)

def get_escaped_redis_key(cache_key: str) -> str:
    if DEPLOYMENT_TYPE:
        return f'{DEPLOYMENT_TYPE}:{cache_key}'
    return cache_key

def safe_redis_get_json(cache_key):
    try:
        _cache_key = get_escaped_redis_key(cache_key)
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, port=REDIS_SERVICE_PORT, socket_connect_timeout=3)
        value = redis_client.get(_cache_key)
        if value:
            logger.info('Loaded {} from redis'.format(_cache_key))
            return json.loads(value)
    except ValueError as e:
        logger.warning('Unable to fetch "{}" from redis:\t{}'.format(_cache_key, str(e)))
    except Exception as e:
        logger.error('Unable to connect to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
    return None


def safe_redis_set_json(cache_key, value, expire=None):
    try:
        _cache_key = get_escaped_redis_key(cache_key)
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, port=REDIS_SERVICE_PORT, socket_connect_timeout=3)
        redis_client.set(_cache_key, json.dumps(value))
        if expire:
            redis_client.expire(_cache_key, expire)
    except Exception as e:
        logger.error('Unable to write to redis host {}: {}'.format(REDIS_SERVICE_HOSTNAME, str(e)))
