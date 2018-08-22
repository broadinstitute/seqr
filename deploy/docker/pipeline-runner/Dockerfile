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
    vim \
    wget \
    xterm

# install jdk-8
RUN echo deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main >> /etc/apt/sources.list.d/java-8-debian.list
RUN echo deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main >> /etc/apt/sources.list.d/java-8-debian.list
RUN echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections
RUN echo debconf shared/accepted-oracle-license-v1-1 seen true | debconf-set-selections

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EEA14886 \
    && apt-get update \
    && apt-get install -y oracle-java8-installer

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

# download VEP - steps based on gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-init.sh and gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh
RUN gsutil cp gs://hail-common/vep/htslib/* /usr/bin/ \
    && gsutil cp gs://hail-common/vep/samtools /usr/bin/ \
    && chmod a+rx  /usr/bin/tabix /usr/bin/bgzip /usr/bin/htsfile /usr/bin/samtools

RUN mkdir -p /vep/homo_sapiens /vep/loftee_data_grch37 /vep/loftee_data_grch38 \
    && gsutil -m cp -r gs://hail-common/vep/vep/loftee /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/ensembl-tools-release-85 /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/GRCh37/loftee_data /vep/loftee_data_grch37  \
    && gsutil -m cp -r gs://hail-common/vep/vep/GRCh38/loftee_data /vep/loftee_data_grch38  \
    && gsutil -m cp -r gs://hail-common/vep/vep/Plugins /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh37 /vep/homo_sapiens/ \
    && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh38 /vep/homo_sapiens/

# install perl dependencies of generate_pedigree_images command which generates static images using HaploPainter.pl
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libglib2.0-bin \
    libglib2.0-0 \
    libgtk2.0-dev \
    libpango1.0-dev

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest \
        Cairo \
        DBI \
        Gtk2 \
        Tk \
        Sort::Naturally

# install database clients for debugging
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4 \
    && echo "deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/4.0 main" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list \
    && apt-get update && apt-get install -y \
        mongodb-org-tools \
        mongodb-org-shell

RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools

# install hail
RUN cd /usr/local \
    && wget -nv https://archive.apache.org/dist/spark/spark-2.0.2/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

RUN pip install decorator==4.2.1    # fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468

RUN wget https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-latest-hadoop2.jar -O /usr/local/spark-2.0.2-bin-hadoop2.7/jars/gcs-connector-latest-hadoop2.jar

# install picard
#RUN mkdir /picard \
#    && cd /picard \
#    && wget https://github.com/broadinstitute/picard/releases/download/2.15.0/picard.jar

# download LiftoverChain files
#RUN mkdir -p /reference-data \
#    && cd /reference-data \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz

# install more VEP dependencies
COPY vep-gcloud-grch37.properties /vep
COPY vep-gcloud-grch38.properties /vep

RUN ln -s /vep/ensembl-tools-release-85/scripts/variant_effect_predictor /vep/variant_effect_predictor \
    && gsutil cp gs://hail-common/vep/vep/GRCh37/run_hail_vep85_GRCh37_vcf.sh /vep/run_hail_vep85_GRCh37_vcf.sh  \
    && gsutil cp gs://hail-common/vep/vep/GRCh38/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_GRCh38_vcf.sh  \
    && chmod a+rx /vep/run_hail_vep85_GRCh37_vcf.sh \
    && chmod a+rx /vep/run_hail_vep85_GRCh38_vcf.sh

WORKDIR /

# install hail, seqr, hail-elasticsearch-pipelines
RUN git clone --branch 0.1 https://github.com/broadinstitute/hail.git \
    && cd /hail \
    && ./gradlew -Dspark.version=2.0.2 shadowJar archiveZip

RUN git clone https://github.com/macarthur-lab/seqr.git

RUN git clone https://github.com/macarthur-lab/hail-elasticsearch-pipelines.git

WORKDIR /seqr

# install seqr dependencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/requirements.txt \
    && pip install --upgrade -r requirements.txt \
    && pip install --upgrade pip jupyter


COPY shared/config/*.py /seqr_settings/

# install more VEP dependencies
RUN /usr/bin/cpanm --installdeps --with-recommends --notest \
    DBI \
    Set::IntervalTree \
    PerlIO::gzip

RUN /usr/bin/cpanm --notest CGI
RUN /usr/bin/cpanm --notest JSON

# run VEP on the 1-variant VCF to create fasta.index file
RUN gsutil cp gs://hail-common/vep/vep/1var.vcf /vep  \
    && /vep/run_hail_vep85_GRCh37_vcf.sh /vep/1var.vcf \
    && /vep/run_hail_vep85_GRCh38_vcf.sh /vep/1var.vcf

ENV TERM=xterm
ENV PYTHONPATH="$PYTHONPATH:/seqr:/seqr_settings:/hail-elasticsearch-pipelines"

COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/bashrc /root/.bashrc

COPY bashrc_custom /root/.bashrc_custom
COPY entrypoint.sh /

COPY core-site.xml /usr/local/spark-2.0.2-bin-hadoop2.7/conf/

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
