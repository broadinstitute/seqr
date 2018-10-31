#!/usr/bin/env bash

set +x
set +x
if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi

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

echo Done

set +x