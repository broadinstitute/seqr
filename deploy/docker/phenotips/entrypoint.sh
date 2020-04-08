#!/bin/bash

# Stop PhenoTips when `docker stop` is called.
trap './stop.sh' SIGTERM

env

echo Current Directory: $(pwd)

set -x

# init phenotips db unless it already exists
if ! psql --host postgres -U postgres -l | grep xwiki; then

  psql --host postgres -U postgres -c 'CREATE DATABASE xwiki';
  psql --host postgres -U postgres -c "CREATE ROLE xwiki WITH CREATEDB LOGIN PASSWORD 'xwiki'";
  psql --host postgres -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE xwiki TO xwiki';

  PGPASSWORD=xwiki psql --host postgres -U xwiki xwiki -f /init_phenotips_db.sql
fi


# turn on debugging
#if [ "$PT_DEBUG" = "true" ]; then
#   export START_OPTS="$START_OPTS -Xdebug -Xnoagent -Djava.compiler=NONE -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=5005"
#fi

# start PhenoTips
./start.sh
