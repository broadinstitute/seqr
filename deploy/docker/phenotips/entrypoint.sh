#!/bin/bash

# Stop what we're doing when `docker stop` is called.
trap './stop.sh' SIGTERM

env


echo Current Directory: $(pwd)

# update config files
sed -i s/connection.url\"\>jdbc\:postgresql\:xwiki/connection.url\"\>jdbc:postgresql:\\\/\\\/postgres-svc:5432\\\/xwiki/g  ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

if [ -n "$POSTGRES_USERNAME" ]; then
    sed -i s/connection.username\"\>postgres\</connection.username\"\>$(echo $POSTGRES_USERNAME)\</g  ./webapps/phenotips/WEB-INF/hibernate.cfg.xml
fi

if [ -n "$POSTGRES_PASSWORD" ]; then
    sed -i s/connection.password\"\>\</connection.password\"\>$(echo $POSTGRES_PASSWORD)\</g  ./webapps/phenotips/WEB-INF/hibernate.cfg.xml
fi

# turn on debugging
#if [ "$PT_DEBUG" = "true" ]; then
#   export START_OPTS="$START_OPTS -Xdebug -Xnoagent -Djava.compiler=NONE -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=5005"
#fi

# start PhenoTips, background it, and wait.
# this is necessary because otherwise the trap does not catch the SIGTERM.
./start.sh &
wait
