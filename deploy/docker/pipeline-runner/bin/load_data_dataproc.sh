#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1
SAMPLE_TYPE=$2
INDEX_NAME=$3
GS_BUCKET=$4
INPUT_FILE_PATH=$5

case ${BUILD_VERSION} in
  38)
    FULL_BUILD_VERSION=GRCh38
    ;;
  37)
    FULL_BUILD_VERSION=GRCh37
    ;;
  *)
    echo "Invalid build '${BUILD_VERSION}', should be 37 or 38"
    exit 1
esac

SOURCE_FILE=${GS_BUCKET}${INPUT_FILE_PATH}
DEST_FILE="${SOURCE_FILE/.*/}".mt
REFERENCE_DATA_BUCKET=${GS_BUCKET}/reference_data/${FULL_BUILD_VERSION}

cd /hail-elasticsearch-pipelines/luigi_pipeline

# create dataproc cluster
hailctl dataproc start \
    --pkgs luigi,google-api-python-client \
    --zone us-central1-b \
    --vep ${FULL_BUILD_VERSION} \
    --max-idle 30m \
    --num-workers 2 \
    --num-preemptible-workers 12 \
    seqr-loading-cluster

# submit annotation job to dataproc cluster
hailctl dataproc submit seqr-loading-cluster \
    seqr_loading.py --pyfiles "lib,../hail_scripts" \
    SeqrVCFToMTTask --local-scheduler \
         --source-paths "${SOURCE_FILE}" \
         --dest-path "${DEST_FILE}" \
         --genome-version "${BUILD_VERSION}" \
         --sample-type "${SAMPLE_TYPE}" \
         --vep-config-json-path "${REFERENCE_DATA_BUCKET}/vep-${FULL_BUILD_VERSION}-loftee-dataproc.json" \
         --reference-ht-path  "${REFERENCE_DATA_BUCKET}/combined_reference_data_grch${BUILD_VERSION}.ht" \
         --clinvar-ht-path "${REFERENCE_DATA_BUCKET}/clinvar.${FULL_BUILD_VERSION}.ht"

JOB_ID=$(gcloud dataproc jobs list)    # run this to get the dataproc job id
gcloud dataproc jobs wait "${JOB_ID}"  # view jobs logs and wait for the job to complete

# load the annotated dataset into your local elasticsearch instance
python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
     --dest-path "${DEST_FILE}" \
     --es-host elasticsearch  \
     --es-index "${INDEX_NAME}"
