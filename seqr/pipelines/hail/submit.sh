#!/usr/bin/env bash

# Run the python script on spark
#CLUSTER='seqr-pipeline-cluster-grch37-2'

CLUSTER=$(gcloud dataproc clusters list | cut -f 1 -d \ | grep -v NAME | grep seqr | head -n 1)
if [ -z $CLUSTER ]; then
    echo "ERROR: cluster doesn\'t exist"
    exit 0
fi

HASH=$(gsutil cat gs://hail-common/latest-hash.txt)
#HAIL_ZIP=gs://hail-common/pyhail-hail-is-master-${HASH}.zip
#HAIL_JAR=gs://hail-common/hail-hail-is-master-all-spark2.0.2-${HASH}.jar

HAIL_ZIP=gs://seqr-hail/hail-jar/hail-python.zip
HAIL_JAR=gs://seqr-hail/hail-jar/hail-all-spark.jar

echo $HAIL_JAR
echo $HAIL_ZIP

#HAIL_JAR=gs://seqr-hail/hail-jar/hail-all-spark.jar
#HAIL_ZIP=gs://seqr-hail/hail-jar/hail-python.zip
#gsutil cp ~/code/hail-repo/build/libs/hail-all-spark.jar        $HAIL_JAR
#gsutil cp ~/code/hail-repo/build/distributions/hail-python.zip  $HAIL_ZIP

# submit VEP job
set -x

SCRIPT_NAME=$1

UTILS_ZIP=/tmp/utils.zip
zip -r $UTILS_ZIP utils

gcloud dataproc jobs submit pyspark \
  --cluster=$CLUSTER \
  --files=$HAIL_JAR \
  --py-files=$HAIL_ZIP,$UTILS_ZIP \
  --properties="spark.files=./$(basename ${HAIL_JAR}),spark.driver.extraClassPath=./$(basename ${HAIL_JAR}),spark.executor.extraClassPath=./$(basename ${HAIL_JAR})" \
  "$SCRIPT_NAME" -- "${@:2}"
