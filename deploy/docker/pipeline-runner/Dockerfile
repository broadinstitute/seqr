FROM perl:5.20

MAINTAINER MacArthur Lab

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

# install jdk-8 for running hail locally
RUN echo deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main >> /etc/apt/sources.list.d/java-8-debian.list
RUN echo deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main >> /etc/apt/sources.list.d/java-8-debian.list
RUN echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections
RUN echo debconf shared/accepted-oracle-license-v1-1 seen true | debconf-set-selections

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EEA14886 \
    && apt-get update \
    && apt-get install -y oracle-java8-installer \
    && apt-get install -y oracle-java8-set-default

# install python and gcloud utils
RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py \
    && pip install --upgrade setuptools

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && curl https://sdk.cloud.google.com | bash \
    && apt-get install -y lsb gcc python-dev python-setuptools libffi-dev libssl-dev \
    && pip install gsutil

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update&& apt-get install -y google-cloud-sdk

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
