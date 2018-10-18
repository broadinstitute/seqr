#!/usr/bin/env bash

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


# install legacy resources
wget -N https://storage.googleapis.com/seqr-reference-data/seqr-resource-bundle.tar.gz -O data/reference_data/seqr-resource-bundle.tar.gz
tar xzf data/reference_data/seqr-resource-bundle.tar.gz -C data/reference_data/

rm data/reference_data/seqr-resource-bundle.tar.gz

python -u manage.py load_resources
python -u manage.py load_omim
