#!/bin/bash

echo "000_init.sh is running"

env

set -x

# cp /root/postgresql.conf /var/lib/postgresql/data/postgresql.conf
# chmod 444 /var/lib/postgresql/data/postgresql.conf

touch /tmp/healthy