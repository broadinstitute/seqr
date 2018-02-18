import logging
import settings

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
import elasticsearch

from settings import LOGIN_URL

logger = logging.getLogger(__name__)


@staff_member_required(login_url=LOGIN_URL)
def elasticsearch_status(request):
    client = elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)

    indices = []
    for index in client.cat.indices(format="json", h="*"):
        if index['index'] == '.kibana':
            continue
        indices.append({k.replace('.', '_'): v for k, v in index.items()})

    return render(request, "staff/elasticsearch_status.html", {
        'indices': indices,
    })
