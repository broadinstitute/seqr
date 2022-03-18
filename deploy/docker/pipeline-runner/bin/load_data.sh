#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1
SAMPLE_TYPE=$2
INDEX_NAME=$3
INPUT_FILE_PATH=$4

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

SOURCE_FILE=/input_vcfs/${INPUT_FILE_PATH}
DEST_FILE="${SOURCE_FILE/.*/}".mt

python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
    --reference-ht-path "/seqr-reference-data/${FULL_BUILD_VERSION}/combined_reference_data_grch${BUILD_VERSION}.ht" \
    --clinvar-ht-path "/seqr-reference-data/${FULL_BUILD_VERSION}/clinvar.${FULL_BUILD_VERSION}.ht" \
    --vep-config-json-path "/vep_configs/vep-${FULL_BUILD_VERSION}-loftee.json" \
    --es-host elasticsearch \
    --es-index-min-num-shards 1 \
    --sample-type "${SAMPLE_TYPE}" \
    --es-index "${INDEX_NAME}" \
    --genome-version "${BUILD_VERSION}" \
    --source-paths "${SOURCE_FILE}" \
    --dest-path "${DEST_FILE}"
