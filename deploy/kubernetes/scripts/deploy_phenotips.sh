#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

echo Postgres Url: ${POSTGRES_HOST}:${POSTGRES_PORT}
echo Postgres Username: $POSTGRES_USERNAME
echo Postgres Password: $POSTGRES_PASSWORD

# delete any previous deployments
kubectl delete -f configs/phenotips/phenotips-deployment.yaml
kubectl delete -f configs/phenotips/phenotips-service.yaml

# create a clean database
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / )
kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database xwiki'
kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database xwiki'

# update config files
sed -i '' s/connection.url\"\>jdbc\:postgresql\:xwiki/connection.url\"\>jdbc:postgresql:\\\/\\\/${POSTGRES_HOST}:${POSTGRES_PORT}\\\/xwiki/g docker/phenotips/config/hibernate.cfg.xml
sed -i '' s/connection.username\"\>postgres/connection.username\"\>${POSTGRES_USERNAME}/g docker/phenotips/config/hibernate.cfg.xml
sed -i '' s/connection.password\"\>/connection.password\"\>${POSTGRES_PASSWORD}/g docker/phenotips/config/hibernate.cfg.xml

# build docker image
FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/phenotips  docker/phenotips/

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/phenotips
fi

# deploy to kubernetes
kubectl create -f configs/phenotips/phenotips-deployment.yaml --record
kubectl create -f configs/phenotips/phenotips-service.yaml --record
