import elasticsearch

import settings

VARIANT_DOC_TYPE = 'variant'


def get_es_client():
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)
