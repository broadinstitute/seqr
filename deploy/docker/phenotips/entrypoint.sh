#!/bin/bash

# Stop what we're doing when `docker stop` is called.
trap './stop.sh' SIGTERM

env

# turn on debugging
#if [ "$PT_DEBUG" = "true" ]; then
#   export START_OPTS="$START_OPTS -Xdebug -Xnoagent -Djava.compiler=NONE -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=5005"
#fi

# start PhenoTips, background it, and wait.
# this is necessary because otherwise the trap does not catch the SIGTERM.
./start.sh &
wait
