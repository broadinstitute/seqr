#!/usr/bin/env bash

set +x

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi

#set +x
#echo
#echo "==== Installing legacy resources ===="
#echo

#mkdir -p data/reference_data

# install legacy resources
#wget -nv https://storage.googleapis.com/seqr-reference-data/seqr-resource-bundle.tar.gz -O data/reference_data/seqr-resource-bundle.tar.gz
#tar xzf data/reference_data/seqr-resource-bundle.tar.gz -C data/reference_data/
#rm data/reference_data/seqr-resource-bundle.tar.gz

#python -u manage.py load_resources
#python -u manage.py load_omim

echo "===== Install spark ===="
set -x

SPARK_VERSION="spark-2.0.2-bin-hadoop2.7"

cd ${SEQR_BIN_DIR} \
    && wget -nv https://archive.apache.org/dist/spark/spark-2.0.2/${SPARK_VERSION}.tgz \
    && tar xzf ${SPARK_VERSION}.tgz
#    && rm spark-2.0.2-bin-hadoop2.7.tgz

export SPARK_HOME=${SEQR_BIN_DIR}'/'${SPARK_VERSION}
echo 'export SPARK_HOME='${SPARK_HOME} >> ~/.bashrc

set +x
echo
echo "==== Install data loading pipeline ===="
echo
set -x

# fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468
sudo $(which pip) install --ignore-installed decorator==4.2.1

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

# install google storage connector which allows hail to access vds's in google buckets without downloading them first
cp ${SEQR_DIR}/hail_elasticsearch_pipelines/hail_builds/v01/gcs-connector-1.6.10-hadoop2.jar ${SPARK_HOME}/jars/
cp ${SEQR_DIR}/deploy/docker/pipeline-runner/config/core-site.xml ${SPARK_HOME}/conf/

mkdir -p ${SEQR_DIR}/vep/loftee_data_grch37 ${SEQR_DIR}/vep/loftee_data_grch38 ${SEQR_DIR}/vep/homo_sapiens
sudo ln -s ${SEQR_DIR}/vep /vep
sudo chmod -R 777 /vep

if [ ! -f /usr/local/bin/perl ]
then
    sudo ln -s /usr/bin/perl /usr/local/bin/perl
fi

# copy large data files
sudo mv /etc/boto.cfg /etc/boto.cfg.aside  # /etc/boto.cfg leads to "ImportError: No module named google_compute_engine" on gcloud Ubuntu VMs, so move it out of the way

[ ! -d /vep/loftee_data_grch37/loftee_data ] && gsutil -m cp -n -r gs://hail-common/vep/vep/GRCh37/loftee_data /vep/loftee_data_grch37
[ ! -d /vep/loftee_data_grch38/loftee_data ] && gsutil -m cp -n -r gs://hail-common/vep/vep/GRCh38/loftee_data /vep/loftee_data_grch38
[ ! -d /vep/homo_sapiens/85_GRCh37 ] && gsutil -m cp -n -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh37 /vep/homo_sapiens
[ ! -d /vep/homo_sapiens/85_GRCh38 ] && gsutil -m cp -n -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh38 /vep/homo_sapiens

if [ ! -f /vep/variant_effect_predictor ]; then
    gsutil -m cp -n -r gs://hail-common/vep/vep/ensembl-tools-release-85 /vep
    gsutil -m cp -n -r gs://hail-common/vep/vep/Plugins /vep
    ln -s /vep/ensembl-tools-release-85/scripts/variant_effect_predictor /vep/variant_effect_predictor
fi

if [ ! -f /vep/1var.vcf ]; then
    cp -r ${SEQR_DIR}/hail_elasticsearch_pipelines/loftee /vep
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch38.properties /vep/vep-gcloud-grch38.properties
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/vep-gcloud-grch37.properties /vep/vep-gcloud-grch37.properties
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh37_vcf.sh /vep/run_hail_vep85_GRCh37_vcf.sh
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_GRCh38_vcf.sh
    cp ${SEQR_DIR}/hail_elasticsearch_pipelines/gcloud_dataproc/vep_init/1var.vcf /vep/1var.vcf

    # (re)create the fasta index VEP uses
    rm /vep/homo_sapiens/85_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa.index
    /vep/run_hail_vep85_GRCh37_vcf.sh /vep/1var.vcf

    # (re)create the fasta index VEP uses
    rm /vep/homo_sapiens/85_GRCh38/Homo_sapiens.GRCh38.dna.primary_assembly.fa.index
    /vep/run_hail_vep85_GRCh38_vcf.sh /vep/1var.vcf
fi


set +x

echo Done
