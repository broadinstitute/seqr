#!/usr/bin/env bash

./seqr/deploy/install_local.step1.install_mongo.sh
./seqr/deploy/install_local.step2.install_postgres.sh
./seqr/deploy/install_local.step3.elasticsearch.sh
./seqr/deploy/install_local.step4.kibana.sh
./seqr/deploy/install_local.step5.install_redis.sh
./seqr/deploy/install_local.step6.install_seqr.sh
./seqr/deploy/install_local.step7.install_phenotips.sh
./seqr/deploy/install_local.step8.install_pipeline_runner.sh
