#!/usr/bin/env bash

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run previous install step."
    exit 1
fi

cd ${SEQR_DIR}
./deploy/install_local.step1.install_mongo.sh
./deploy/install_local.step2.install_postgres.sh
./deploy/install_local.step3.elasticsearch.sh
./deploy/install_local.step4.kibana.sh
./deploy/install_local.step5.install_redis.sh
./deploy/install_local.step6.install_seqr.sh
./deploy/install_local.step7.install_phenotips.sh
#./deploy/install_local.step8.install_pipeline_runner.sh
