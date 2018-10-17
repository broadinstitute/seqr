#!/usr/bin/env bash

wget https://raw.githubusercontent.com/macarthur-lab/seqr/deploy_code_hail_elasticsearch_repo_integration/deploy/install_local.step0.set_env_vars.sh
source ./install_local.step0.set_env_vars.sh

wget https://raw.githubusercontent.com/macarthur-lab/seqr/deploy_code_hail_elasticsearch_repo_integration/deploy/install_local.step1.clone_seqr_repo.sh
./install_local.step1.clone_seqr_repo.sh
chmod 777 ./install_local.step1.clone_seqr_repo.sh

./seqr/deploy/install_local.step2.install_mongo.sh
./seqr/deploy/install_local.step3.install_postgres.sh
./seqr/deploy/install_local.step4.elasticsearch.sh
./seqr/deploy/install_local.step5.kibana.sh
./seqr/deploy/install_local.step6.install_redis.sh
./seqr/deploy/install_local.step7.install_seqr.sh
./seqr/deploy/install_local.step8.install_phenotips.sh
./seqr/deploy/install_local.step9.install_pipeline_runner.sh
