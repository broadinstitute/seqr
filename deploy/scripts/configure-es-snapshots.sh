#!/usr/bin/env bash

ELASTICSEARCH_SNAPSHOTS_BUCKET=$1

kubectl port-forward elasticsearch-es-http 9200

curl -u "elastic:$ELASTICSEARCH_PASSWORD" -X PUT "localhost:9200/_snapshot/snapshot_storage?pretty" -H 'Content-Type: application/json' --data @- <<EOF
{
   "type": "gcs",
   "settings": {
     "bucket": "${ELASTICSEARCH_SNAPSHOTS_BUCKET}",
     "client": "default",
     "compress": true
   }
}
EOF


curl -u "elastic:$ELASTICSEARCH_PASSWORD" -X PUT "localhost:9200/_slm/policy/monthly-snapshots?pretty" -H 'Content-Type: application/json' -d'
{
  "schedule": "0 0 0 1 * ?", 
  "name": "<monthly-snap-{yyyy.MM.dd}>", 
  "repository": "snapshot_storage", 
  "retention": { 
    "expire_after": "90d", 
    "min_count": 2, 
    "max_count": 5 
  }
}
'
