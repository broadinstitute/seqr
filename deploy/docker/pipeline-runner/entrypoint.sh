#!/usr/bin/env bash

set -x

env

source ~/.bashrc

# init gcloud
if [ $GCLOUD_PROJECT ]; then
    gcloud config set project $GCLOUD_PROJECT
fi

if [ $GCLOUD_ZONE ]; then
    gcloud config set compute/zone $GCLOUD_ZONE
fi

mkdir -p /vep/loftee_data_grch37 /vep/loftee_data_grch38 /vep/homo_sapiens

# copy large data files
[ ! -d /vep/loftee_data_grch37/loftee_data ] && gsutil -m cp -r gs://hail-common/vep/vep/GRCh37/loftee_data /vep/loftee_data_grch37
[ ! -d /vep/loftee_data_grch38/loftee_data ] && gsutil -m cp -r gs://hail-common/vep/vep/GRCh38/loftee_data /vep/loftee_data_grch38
[ ! -d /vep/homo_sapiens/85_GRCh37 ] && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh37 /vep/homo_sapiens
[ ! -d /vep/homo_sapiens/85_GRCh38 ] && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh38 /vep/homo_sapiens

if [ ! -f /vep/variant_effect_predictor ]; then
    gsutil -m cp -r gs://hail-common/vep/vep/ensembl-tools-release-85 /vep
    gsutil -m cp -r gs://hail-common/vep/vep/Plugins /vep
    ln -s /vep/ensembl-tools-release-85/scripts/variant_effect_predictor /vep/variant_effect_predictor
fi

if [ ! -f /vep/1var.vcf ]; then
    cp -r /hail-elasticsearch-pipelines/loftee /vep
    cp /hail-elasticsearch-pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch38.properties /vep/vep-gcloud-grch38.properties
    cp /hail-elasticsearch-pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch37.properties /vep/vep-gcloud-grch37.properties
    cp /hail-elasticsearch-pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh37_vcf.sh /vep/run_hail_vep85_GRCh37_vcf.sh
    cp /hail-elasticsearch-pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_GRCh38_vcf.sh
    cp /hail-elasticsearch-pipelines/gcloud_dataproc/vep_init/1var.vcf /vep/1var.vcf

    # run VEP on the 1-variant VCF to create fasta.index file
    /vep/run_hail_vep85_GRCh37_vcf.sh /vep/1var.vcf
    /vep/run_hail_vep85_GRCh38_vcf.sh /vep/1var.vcf
fi

if [ -e "/.config/service-account-key.json" ]; then
    # authenticate to google cloud using service account
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud auth activate-service-account --key-file /.config/service-account-key.json
    cp /.config/boto /root/.boto
fi

# launch jupyter notebook in background
mkdir /ipython_notebooks
cd /ipython_notebooks
nohup jupyter notebook --ip=0.0.0.0 --port=30005 --allow-root --NotebookApp.token='' &

# sleep to keep image running even if the jupyter notebook is killed / restarted
sleep 1000000000000
