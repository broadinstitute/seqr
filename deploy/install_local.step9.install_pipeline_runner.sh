#!/usr/bin/env bash

set +x
#set +x
#echo
#echo "==== Installing legacy resources ===="
#echo

cd ${SEQR_DIR}

#mkdir -p data/reference_data

# install legacy resources
#wget -nv https://storage.googleapis.com/seqr-reference-data/seqr-resource-bundle.tar.gz -O data/reference_data/seqr-resource-bundle.tar.gz
#tar xzf data/reference_data/seqr-resource-bundle.tar.gz -C data/reference_data/
#rm data/reference_data/seqr-resource-bundle.tar.gz

#python -u manage.py load_resources
#python -u manage.py load_omim

set +x
echo
echo "==== Installing data loading pipeline ===="
echo
set -x

# install google storage connector which allows hail to access vds in google buckets without downloading them first
cd ${SEQR_BIN_DIR} \
    && wget -nv https://archive.apache.org/dist/spark/spark-2.0.2/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf spark-2.0.2-bin-hadoop2.7.tgz \
    && rm spark-2.0.2-bin-hadoop2.7.tgz

# fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468
sudo $(which pip) install decorator==4.2.1

# install jupyter
sudo $(which pip) install --upgrade pip jupyter

# download and install VEP - steps based on gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-init.sh and gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh
wget -nv https://raw.github.com/miyagawa/cpanminus/master/cpanm -O cpanm && chmod +x cpanm
sudo chown -R $USER ~/.cpanm/  # make sure the user owns .cpanm
# VEP dependencies
cpanm --sudo --notest Set::IntervalTree
cpanm --sudo --notest PerlIO::gzip
cpanm --sudo --notest DBI
cpanm --sudo --notest CGI
cpanm --sudo --notest JSON
# LoFTEE dependencies
cpanm --sudo --notest DBD::SQLite
cpanm --sudo --notest List::MoreUtils

# copy hail build
sudo mkdir -p /hail/build/libs /hail/build/distributions \
    && sudo chmod -R +x /hail \
    && cp ${SEQR_DIR}/hail_elasticsearch_pipelines/hail_builds/v01/hail-v01-10-8-2018-90c855449.zip /hail/build/distributions/hail-python.zip \
    && cp ${SEQR_DIR}/hail_elasticsearch_pipelines/hail_builds/v01/hail-v01-10-8-2018-90c855449.jar /hail/build/libs/hail-all-spark.jar \
    && cp ${SEQR_DIR}/hail_elasticsearch_pipelines/hail_builds/v01/gcs-connector-1.6.10-hadoop2.jar ${SEQR_BIN_DIR}/spark-2.0.2-bin-hadoop2.7/jars/


cp ${SEQR_DIR}/deploy/docker/pipeline-runner/config/core-site.xml ${SEQR_BIN_DIR}/spark-2.0.2-bin-hadoop2.7/conf/

sudo mkdir -p /vep/loftee_data_grch37 /vep/loftee_data_grch38 /vep/homo_sapiens
sudo chmod 777 -R /vep

# copy large data files
sudo mv /etc/boto.cfg /etc/boto.cfg.aside  # /etc/boto.cfg leads to "ImportError: No module named google_compute_engine" on gcloud Ubuntu VMs, so move it out of the way

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
    cp -r ${SEQR_DIR}/hail_elasticsearch_pipelines/loftee /vep
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch38.properties /vep/vep-gcloud-grch38.properties
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch37.properties /vep/vep-gcloud-grch37.properties
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh37_vcf.sh /vep/run_hail_vep85_GRCh37_vcf.sh
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_GRCh38_vcf.sh
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/1var.vcf /vep/1var.vcf

    # run VEP on the 1-variant VCF to create fasta.index file
    /vep/run_hail_vep85_GRCh37_vcf.sh /vep/1var.vcf
    /vep/run_hail_vep85_GRCh38_vcf.sh /vep/1var.vcf
fi


set +x

