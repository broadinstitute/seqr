#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

COMPONENT=$2

case ${COMPONENT} in
  hail-search)
    PORT=5000
    NAME='service/seqr-hail-search'
    ;;
  redis)
    PORT=6379
    ;;
  seqr)
    PORT=8000
    OPEN_BROWSER=true
    ;;
  *)
    echo "Invalid component '${COMPONENT}'"
    exit 1
esac

if [[ ! ${NAME} ]] ; then
  NAME=$("${DIR}"/utils/get_pod_name.sh "$@")
fi

kubectl port-forward "${NAME}" "${PORT}" &

if [[ ${OPEN_BROWSER} ]] ; then
  sleep 3
  open http://localhost:${PORT}
fi

wait
