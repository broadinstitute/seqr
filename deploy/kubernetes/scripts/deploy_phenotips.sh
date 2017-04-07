#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/phenotips/phenotips-deployment.yaml
kubectl delete -f configs/phenotips/phenotips-service.yaml

# update config files
sed -i '' s/connection.url\"\>jdbc\:postgresql\:xwiki/connection.url\"\>jdbc:postgresql:\\\/\\\/postgres-svc:5432\\\/xwiki/g docker/phenotips/config/hibernate.cfg.xml
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


# the 1st time PhenoTips is opened, it goes through an initialization step
sleep 20

PHENOTIPS_POD_NAME=$( kubectl get pods -o=name | grep 'phenotips-' | cut -f 2 -d / | tail -n 1)
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html

sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html
