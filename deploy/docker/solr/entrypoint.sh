#!/usr/bin/env bash

set -x

su -c '/usr/local/solr-6.4.2/bin/solr start -p 30002 -f -c ' solr
# -s /solr-data
echo Started!!


# sleep indefinitely to prevent container from terminating
sleep 1000000000000
