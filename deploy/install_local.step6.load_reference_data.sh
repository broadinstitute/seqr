#!/usr/bin/env bash

set +x
set +x
echo
echo "==== Load reference data ===="
echo
set -x

cd ${SEQR_DIR}

mkdir -p data/reference_data

# install new reference data
REFERENCE_DATA_BACKUP_FILE=data/reference_data/gene_reference_data_backup.gz

wget -N https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz -O ${REFERENCE_DATA_BACKUP_FILE}

USERNAME=postgres
DATABASE_NAME=seqrdb

psql -U $USERNAME postgres -c "DROP DATABASE $DATABASE_NAME"
psql -U $USERNAME postgres -c "CREATE DATABASE $DATABASE_NAME"
psql -U $USERNAME $DATABASE_NAME <  <(gunzip -c ${REFERENCE_DATA_BACKUP_FILE})

set +x