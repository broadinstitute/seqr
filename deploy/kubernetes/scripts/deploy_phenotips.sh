#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

echo Postgres Url: ${POSTGRES_HOST}:${POSTGRES_PORT}
echo Postgres Username: $POSTGRES_USERNAME
echo Postgres Password: $POSTGRES_PASSWORD

sed -i '' s/connection.url\"\>jdbc\:postgresql\:xwiki/connection.url\"\>jdbc:postgresql:\\\/\\\/${POSTGRES_HOST}:${POSTGRES_PORT}\\\/xwiki/g docker/phenotips/config/hibernate.cfg.xml
sed -i '' s/connection.username\"\>postgres/connection.username\"\>${POSTGRES_USERNAME}/g docker/phenotips/config/hibernate.cfg.xml
sed -i '' s/connection.password\"\>/connection.password\"\>${POSTGRES_PASSWORD}/g docker/phenotips/config/hibernate.cfg.xml

if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
else
    FORCE_ARG=
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/phenotips  docker/phenotips/

if [ "DEPLOY_TO_GOOGLE_CLOUD" = true ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/phenotips
fi

kubectl delete -f configs/phenotips/phenotips-deployment.yaml
kubectl create -f configs/phenotips/phenotips-deployment.yaml --record

kubectl delete -f configs/phenotips/phenotips-service.yaml
kubectl create -f configs/phenotips/phenotips-service.yaml --record
