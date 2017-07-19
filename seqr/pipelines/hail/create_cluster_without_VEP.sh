#!/usr/bin/env bash

CLUSTER=seqr-pipeline-cluster-no-vep

# create cluster
gcloud dataproc clusters create $CLUSTER   \
    --zone us-central1-b  \
    --master-machine-type n1-standard-4  \
    --master-boot-disk-size 100  \
    --num-workers 2  \
    --worker-machine-type n1-standard-4  \
    --worker-boot-disk-size 75 \
    --num-worker-local-ssds 1 \
    --image-version 1.1 \
    --project seqr-project \
    --properties "spark:spark.driver.extraJavaOptions=-Xss4M,spark:spark.executor.extraJavaOptions=-Xss4M,spark:spark.driver.memory=45g,spark:spark.driver.maxResultSize=30g,spark:spark.task.maxFailures=20,spark:spark.yarn.executor.memoryOverhead=30,spark:spark.kryoserializer.buffer.max=1g,hdfs:dfs.replication=1"  \
    --initialization-actions gs://hail-common/hail-init.sh,gs://seqr-hail/init_notebook.py
    #--num-preemptible-workers 4 \

#    gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-init.sh
#    --initialization-actions gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-with-lof-splice-init.sh,gs://hail-common/init_notebook.py

#HDFS_INPUT_PATH=hdfs:/data/$(basename $VCF_PATH)
#HDFS_OUTPUT_PATH=hdfs:/data/out.vcf.bgz

# open ipython notebook
python utils/connect_cluster.py  --name $CLUSTER --port 8088

open http://localhost:8088  # open spark dashboard

