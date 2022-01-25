#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1

# download VEP cache
mkdir -p /vep_data/homo_sapiens
cd /vep_data
CACHE_FILE=homo_sapiens_vep_99_GRCh${BUILD_VERSION}.tar.gz
echo curl -LO http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/${CACHE_FILE}
echo tar xzf ${CACHE_FILE}

# download loftee reference data
mkdir -p /vep_data/loftee_data/GRCh${BUILD_VERSION}/
cd /vep_data/loftee_data/GRCh${BUILD_VERSION}/
gsutil cp gs://seqr-reference-data/vep_data/loftee-beta/GRCh${BUILD_VERSION}.tar .
tar xf GRCh${BUILD_VERSION}.tar

# download seqr reference data
mkdir /seqr-reference-data/GRCh${BUILD_VERSION}
cd /seqr-reference-data/GRCh${BUILD_VERSION}
echo gsutil -m rsync -r gs://seqr-reference-data/GRCh${BUILD_VERSION}/all_reference_data/combined_reference_data_grch${BUILD_VERSION}.ht .
gsutil -m rsync -r gs://seqr-reference-data/GRCh${BUILD_VERSION}/clinvar/clinvar.GRCh${BUILD_VERSION}.2021-11-13.ht .
