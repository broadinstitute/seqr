#!/bin/bash

# Stop PhenoTips when `docker stop` is called.
trap './stop.sh' SIGTERM

env

echo Current Directory: $(pwd)

set -x

# init PhenoTips db
PGPASSWORD=xwiki psql --host postgres --port 5432 -U xwiki xwiki -f /init_phenotips_db.sql

# turn on debugging
#if [ "$PT_DEBUG" = "true" ]; then
#   export START_OPTS="$START_OPTS -Xdebug -Xnoagent -Djava.compiler=NONE -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=5005"
#fi

# start PhenoTips, background it, and wait.
./start.sh &

touch /tmp/ready

sleep 1000000000000

