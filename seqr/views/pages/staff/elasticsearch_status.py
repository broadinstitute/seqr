import json
import logging
from pprint import pprint, pformat
import re

import elasticsearch_dsl
import requests
from collections import defaultdict

import settings

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
import elasticsearch

from seqr.models import Dataset
from settings import LOGIN_URL

logger = logging.getLogger(__name__)


@staff_member_required(login_url=LOGIN_URL)
def elasticsearch_status(request):
    client = elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)

    # look up seqr dataset records
    index_to_dataset = {}
    for dataset in Dataset.objects.all():
        if dataset.dataset_id:
            index_name = dataset.dataset_id
            index_to_dataset[index_name] = dataset

    # get index snapshots
    response = requests.get("http://%s:9200/_snapshot/%s/_all" % (settings.ELASTICSEARCH_SERVICE_HOSTNAME, "callsets"))
    snapshots = json.loads(response.content)

    index_snapshot_states = defaultdict(list)
    for snapshot in snapshots["snapshots"]:
        for index_name in snapshot["indices"]:
            index_snapshot_states[index_name].append(snapshot["state"])

    # get indices
    indices = []
    for index in client.cat.indices(format="json", h="*"):
        #pprint(index)
        index_name = index['index']

        # skip special indices
        if index_name in ['.kibana', 'index_operations_log']:
            continue

        index_json = {k.replace('.', '_'): v for k, v in index.items()}

        index_name = re.sub("_[0-9]{1,2}$", "", index_name)
        if index_name in index_to_dataset:
            index_json['project_guid'] = index_to_dataset[index_name].project.guid
            index_json['project_id'] = index_to_dataset[index_name].project.deprecated_project_id
            index_json['analysis_type'] = index_to_dataset[index_name].analysis_type
            index_json['genome_version'] = index_to_dataset[index_name].genome_version

        if index_name in index_snapshot_states:
            index_json['snapshots'] = ", ".join(set(index_snapshot_states[index_name]))
        indices.append(index_json)

    # get operations log
    s = elasticsearch_dsl.Search(using=client, index="index_operations_log")
    s = s.params(size=5000)
    operations = [doc.to_dict() for doc in s.execute().hits]

    return render(request, "staff/elasticsearch_status.html", {
        'indices': indices,
        'operations': operations,
    })
