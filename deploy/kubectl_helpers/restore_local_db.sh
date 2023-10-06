#!/usr/bin/env bash

set -x -e -u

DEPLOYMENT_TARGET=$1
DB=$2

FILENAME=${DB}_${DEPLOYMENT_TARGET}_backup_$(date +"%Y-%m-%d__%H-%M-%S").gz
GS_FILE=gs://seqr-scratch-temp/${FILENAME}

gcloud sql export sql postgres-"${DEPLOYMENT_TARGET}" "${GS_FILE}" --database="${DB}" --offload
gsutil mv "${GS_FILE}" .

psql postgres -c "DROP DATABASE IF EXISTS ${DB}"
psql postgres -c "CREATE DATABASE ${DB}"
psql "${DB}" < <(gunzip -c "${FILENAME}")
