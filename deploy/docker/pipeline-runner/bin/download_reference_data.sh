#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1
GS_BUCKET=$2

# download reference data
WORKDIR /seqr-reference-data/GRCh38
RUN gsutil -m rsync -r gs://seqr-reference-data/GRCh38/all_reference_data/combined_reference_data_grch38.ht .
#WORKDIR /seqr-reference-data/GRCh37
#RUN gsutil -m rsync -r gs://seqr-reference-data/GRCh37/all_reference_data/combined_reference_data_grch37.ht .

WORKDIR /seqr-reference-data/GRCh38/clinvar
#RUN gsutil -m cp -r gs://seqr-reference-data/GRCh38/clinvar/clinvar.GRCh38.2021-11-13.ht .ls vep

WORKDIR /seqr-reference-data/GRCh37/clinvar
#RUN gsutil -m cp -r gs://seqr-reference-data/GRCh37/clinvar/clinvar.GRCh37.2021-11-13.ht .


gsuitl -m rsync -r /seqr-reference-data/GRCh${BUILD_VERSION} ${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}
gsutil cp /vep_configs/hail_dataproc/vep-GRCh${BUILD_VERSION}-loftee-gcloud.json ${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}