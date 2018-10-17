#!/usr/bin/env bash

./install_local.step0.set_env_vars.sh
./install_local.step1.clone_seqr_repo.sh
./install_local.step2.install_mongo.sh
./install_local.step3.install_postgres.sh
./install_local.step4.elasticsearch.sh
./install_local.step5.kibana.sh
./install_local.step6.install_redis.sh
./install_local.step7.install_seqr.sh
./install_local.step8.install_phenotips.sh
./install_local.step9.install_pipeline_runner.sh
