#!/usr/bin/env bash

echo "==== Installing data loading pipeline ===="
set -x

if [ -z "$PLATFORM" ]; then

    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    :

elif [ $PLATFORM = "centos" ]; then

    :

elif [ $PLATFORM = "ubuntu" ]; then

    :

else
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;



# install commmon utilities
RUN apt-get update && apt-get install -y --fix-missing \
    apt-utils \
    bzip2 \
    cmake \
    curl \
    emacs \
    g++ \
    git \
    htop \
    less \
    nano \
    wget \
    xterm


RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl \
    && chmod +x ./kubectl \
    && mv ./kubectl /usr/local/bin/kubectl

# install google storage connector which allows hail to access vds in google buckets without downloading them first
RUN cd /usr/local \
    && wget -nv https://archive.apache.org/dist/spark/spark-2.0.2/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

# fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468
RUN pip install decorator==4.2.1

# install jupyter
RUN pip install --upgrade pip jupyter

#RUN git clone --branch 0.1 https://github.com/broadinstitute/hail.git \
#    && cd /hail \
#    && ./gradlew -Dspark.version=2.0.2 shadowJar archiveZip


# install picard
#RUN mkdir /picard \
#    && cd /picard \
#    && wget https://github.com/broadinstitute/picard/releases/download/2.15.0/picard.jar

# download LiftoverChain files
#RUN mkdir -p /reference-data \
#    && cd /reference-data \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz

# download and install VEP - steps based on gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-init.sh and gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh
RUN gsutil -m cp gs://hail-common/vep/htslib/* /usr/bin/ \
    && gsutil -m cp gs://hail-common/vep/samtools /usr/bin/ \
    && chmod a+rx  /usr/bin/tabix /usr/bin/bgzip /usr/bin/htsfile /usr/bin/samtools

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm && chmod +x /usr/bin/cpanm
# VEP dependencies
RUN /usr/bin/cpanm --notest Set::IntervalTree
RUN /usr/bin/cpanm --notest PerlIO::gzip
RUN /usr/bin/cpanm --notest DBI
RUN /usr/bin/cpanm --notest CGI
RUN /usr/bin/cpanm --notest JSON
# LoFTEE dependencies
RUN /usr/bin/cpanm --notest DBD::SQLite
RUN /usr/bin/cpanm --notest  List::MoreUtils

# DISABLE_CACHE work-around to force git pull on every docker build, based on https://github.com/docker/docker/issues/1996
ARG DISABLE_CACHE=1

# clone hail-elasticsearch-pipelines
RUN git clone https://github.com/macarthur-lab/hail-elasticsearch-pipelines.git /hail-elasticsearch-pipelines

# copy hail build
RUN mkdir -p /hail/build/libs /hail/build/distributions \
    && cp /hail-elasticsearch-pipelines/hail_builds/v01/hail-v01-10-8-2018-90c855449.zip /hail/build/distributions/hail-python.zip \
    && cp /hail-elasticsearch-pipelines/hail_builds/v01/hail-v01-10-8-2018-90c855449.jar /hail/build/libs/hail-all-spark.jar \
    && cp /hail-elasticsearch-pipelines/hail_builds/v01/gcs-connector-1.6.10-hadoop2.jar /usr/local/spark-2.0.2-bin-hadoop2.7/jars/

ENV TERM=xterm
ENV PYTHONPATH="$PYTHONPATH:/seqr:/seqr_settings:/hail-elasticsearch-pipelines"

COPY config/gitconfig /root/.gitconfig
COPY bashrc /root/.bashrc
COPY config/run_hail_locally.sh /hail-elasticsearch-pipelines
COPY config/run_hail_on_dataproc.sh /hail-elasticsearch-pipelines
COPY config/core-site.xml /usr/local/spark-2.0.2-bin-hadoop2.7/conf/
COPY entrypoint.sh /


WORKDIR /hail-elasticsearch-pipelines

CMD [ "/entrypoint.sh" ]


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


set +x
