#!/usr/bin/env bash

set +x
set +x
echo
echo "==== Annotate and load test dataset. This can take ~24 hours. ===="
echo
set -x

#gs://seqr-reference-data/test-projects/1kg.ped

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi


cd ${SEQR_DIR}/hail_elasticsearch_pipelines

PIPELINE_CPU_LIMIT=2

nohup python2.7 gcloud_dataproc/submit.py --cpu-limit $PIPELINE_CPU_LIMIT --num-executors $PIPELINE_CPU_LIMIT  --run-locally hail_scripts/v01/load_dataset_to_es.py \
    --spark-home $SPARK_HOME --genome-version 37 --project-guid R001_test --sample-type WES --dataset-type VARIANTS \
    --skip-validation  --exclude-hgmd --vep-block-size 10 --es-block-size 10 --num-shards 1 --hail-version 0.1 \
    --use-nested-objects-for-vep --use-nested-objects-for-genotypes \
    gs://seqr-reference-data/test-projects/1kg.vcf.gz \
    2>&1 | grep -v org.apache.parquet.hadoop 2>&1 | grep -v 'Use of uninitialized value' 2>&1 > load_1kg_test_dataset.log  &

set +x

echo Loading process started in background...
echo Log file: $(pwd)/load_1kg_test_dataset.log

cd ..
