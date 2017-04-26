#!/usr/bin/env bash

set -x

env

echo Copying /etc/matchbox-config/ to /matchbox/config/
cp /etc/matchbox-config/* /matchbox/config/

java -jar target/matchbox-0.1.0.jar &

sleep 10000000000
