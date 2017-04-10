#!/bin/bash

echo "002_init.sh is running"

env

set -x

psql -U postgres xwiki < /docker-entrypoint-initdb.d/config/init_phenotips.sql
