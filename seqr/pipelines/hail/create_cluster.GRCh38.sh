#!/usr/bin/env bash

CLUSTER=seqr-pipeline-cluster-grch38

# create cluster
gcloud dataproc clusters create $CLUSTER   \
    --zone us-central1-b  \
    --master-machine-type n1-highmem-2  \
    --master-boot-disk-size 100  \
    --num-workers 2  \
    --worker-machine-type n1-highmem-2  \
    --worker-boot-disk-size 75 \
    --num-worker-local-ssds 1 \
    --num-preemptible-workers 4 \
    --image-version 1.1 \
    --project seqr-project \
    --properties "spark:spark.driver.extraJavaOptions=-Xss4M,spark:spark.executor.extraJavaOptions=-Xss4M,spark:spark.driver.memory=45g,spark:spark.driver.maxResultSize=30g,spark:spark.task.maxFailures=20,spark:spark.yarn.executor.memoryOverhead=30,spark:spark.kryoserializer.buffer.max=1g,hdfs:dfs.replication=1"  \
    --initialization-actions gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh,gs://hail-common/init_notebook.py
#    --initialization-actions gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-with-lof-splice-init.sh,gs://hail-common/init_notebook.py

# open ipython notebook
python utils/connect_cluster.py  --name $CLUSTER

#open http://localhost:4040  # open spark dashboard

