import elasticsearch

import settings

VARIANT_DOC_TYPE = 'variant'


def get_es_client(timeout=10):
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME, timeout=timeout)
