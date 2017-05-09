#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/phenotips/phenotips-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/phenotips/phenotips-service.yaml

# wait for pod to terminate
set +x
while [ "$( kubectl get pods | grep 'phenotips-' | grep Running)" ] || [ "$( kubectl get pods | grep 'phenotips-' | grep Terminating)" ]; do
    echo $(date) - Waiting for phenotips pod to terminate. Current state is: "$( kubectl get pods | grep 'phenotips-' )"
    sleep 5
done
echo $(date) - Done. Current state is: "$( kubectl get pods | grep 'phenotips-' )"
set -x


# reset the db if needed
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1 )
if [ "$RESET_DB" = true ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database xwiki'
fi

if [ "$RESTORE_DB_FROM_BACKUP" != "none" ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database xwiki'
fi

kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database xwiki'

if [ "$RESTORE_DB_FROM_BACKUP" != "none" ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c "create role xwiki"
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c "alter role xwiki password 'xwiki' SUPERUSER"
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'
    kubectl cp $RESTORE_DB_FROM_BACKUP ${POSTGRES_POD_NAME}:/root/$(basename $RESTORE_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- /root/restore_database_backup.sh xwiki /root/$(basename $RESTORE_DB_FROM_BACKUP)
    #kubectl exec $POSTGRES_POD_NAME -- rm /root/$(basename $RESTORE_DB_FROM_BACKUP)
else
    kubectl cp docker/phenotips/init/init_phenotips_db.sql ${POSTGRES_POD_NAME}:/
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres xwiki -f /init_phenotips_db.sql
fi


# update config files
#sed -i '' s/connection.url\"\>jdbc\:postgresql\:xwiki/connection.url\"\>jdbc:postgresql:\\\/\\\/postgres-svc:5432\\\/xwiki/g docker/phenotips/config/hibernate.cfg.xml
#sed -i '' s/connection.username\"\>postgres/connection.username\"\>${POSTGRES_USERNAME}/g docker/phenotips/config/hibernate.cfg.xml
#sed -i '' s/connection.password\"\>/connection.password\"\>${POSTGRES_PASSWORD}/g docker/phenotips/config/hibernate.cfg.xml

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
kubectl create -f configs/phenotips/phenotips-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/phenotips/phenotips-service.yaml --record

# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'phenotips-' | grep Running)" ] || [ "$( kubectl get pods | grep 'phenotips-' | grep Terminating)" ]; do
    echo $(date) - Waiting for phenotips pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'phenotips-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'phenotips-' )"
set -x

#kubectl cp docker/phenotips/init/extension ${PHENOTIPS_POD_NAME}:/phenotips-standalone-1.2.6/data/

# when the PhenoTips website is opened for the 1st time, it triggers a final set of initialization
# steps, so do wget's to trigger this
PHENOTIPS_POD_NAME=$( kubectl get pods -o=name | grep 'phenotips-' | cut -f 2 -d / | tail -n 1)
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html

# until $(curl --output /dev/null --silent --head --fail http://localhost:8080 ); do
#  printf '.'
#  sleep 5
# done
