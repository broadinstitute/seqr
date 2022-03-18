#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1
GS_BUCKET=$2

DEST_BUCKET=${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}

REF_DATA_HT=combined_reference_data_grch${BUILD_VERSION}.ht
gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/all_reference_data/${REF_DATA_HT}" "${DEST_BUCKET}/${REF_DATA_HT}"

CLINVAR_HT=clinvar.GRCh${BUILD_VERSION}.ht
gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/clinvar/${CLINVAR_HT}" "${DEST_BUCKET}/${CLINVAR_HT}"

gsutil cp "/vep_configs/vep-GRCh${BUILD_VERSION}-loftee-dataproc.json" "${DEST_BUCKET}"
