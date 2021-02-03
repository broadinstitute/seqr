#!/usr/bin/env bash

curl -u "kibana:$KIBANA_ES_PASSWORD" -X PUT "${ELASTICSEARCH_SERVICE_HOSTNAME}:9200/_snapshot/snapshot_storage?pretty" -H 'Content-Type: application/json' --data @- <<EOF
{
   "type": "gcs",
   "settings": {
     "bucket": "${ES_SNAPSHOTS_BUCKET}",
     "client": "default",
     "compress": true
   }
}
EOF


curl -u "kibana:$KIBANA_ES_PASSWORD" -X PUT "${ELASTICSEARCH_SERVICE_HOSTNAME}:9200/_slm/policy/monthly-snapshots?pretty" -H 'Content-Type: application/json' -d'
{
  "schedule": "0 0 0 1 * ?",
  "name": "<monthly-snap-{now/d}>",
  "repository": "snapshot_storage",
  "retention": {
    "expire_after": "90d",
    "min_count": 2,
    "max_count": 5
  }
}
'
