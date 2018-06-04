import json
import logging
import re

import elasticsearch_dsl
import requests
from collections import defaultdict

import settings

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
import elasticsearch

from seqr.models import Sample
from settings import LOGIN_URL

logger = logging.getLogger(__name__)

OPERATIONS_LOG = "index_operations_log"

@staff_member_required(login_url=LOGIN_URL)
def elasticsearch_status(request):
    client = elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)

    # get index snapshots
    response = requests.get("http://{0}:{1}/_snapshot/{2}/_all".format(
        settings.ELASTICSEARCH_SERVICE_HOSTNAME, settings.ELASTICSEARCH_PORT, "callsets"))
    snapshots = json.loads(response.content)

    index_snapshot_states = defaultdict(list)
    for snapshot in snapshots["snapshots"]:
        for index_name in snapshot["indices"]:
            index_snapshot_states[index_name].append(snapshot["state"])

    # get indices
    indices = []
    for index in client.cat.indices(format="json", h="*"):
        index_name = index['index']

        # skip special indices
        if index_name in ['.kibana', 'index_operations_log']:
            continue

        index_json = {k.replace('.', '_'): v for k, v in index.items()}

        index_name = re.sub("_[0-9]{1,2}$", "", index_name)

        sample = Sample.objects.filter(elasticsearch_index=index_name).select_related('individual__family__project').only('sample_tye').first()
        if sample:
            project = sample.individual.family.project
            index_json['project_guid'] = project.guid
            index_json['project_id'] = project.deprecated_project_id
            index_json['dataset_type'] = sample.sample_type
            index_json['genome_version'] = project.genome_version

        if index_name in index_snapshot_states:
            index_json['snapshots'] = ", ".join(set(index_snapshot_states[index_name]))
        indices.append(index_json)

    # get operations log
    s = elasticsearch_dsl.Search(using=client, index=OPERATIONS_LOG)
    s = s.params(size=5000)
    operations = [doc.to_dict() for doc in s.execute().hits]

    return render(request, "staff/elasticsearch_status.html", {
        'indices': indices,
        'operations': operations,
        'elasticsearch_host': settings.ELASTICSEARCH_SERVER,
    })
