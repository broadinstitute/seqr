#!/usr/bin/env bash

set -x

su -c '/usr/local/elasticsearch-5.4.3/bin/elasticsearch ' elasticsearch &

echo Started!!


# sleep indefinitely to prevent container from terminating
sleep 1000000000000
