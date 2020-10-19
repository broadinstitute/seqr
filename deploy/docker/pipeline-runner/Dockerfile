FROM bitnami/minideb:stretch

LABEL maintainer="Broad TGG"

# install commmon utilities
RUN install_packages \
    ca-certificates \
    less \
    nano \
    wget \
    curl \
    emacs \
    g++ \
    git \
    htop \
    make \
    autoconf \
    unzip \
    bzip2 \
    zlib1g-dev \
    dpkg-dev \
    build-essential \
    libcurl4-openssl-dev \
    libbz2-dev \
    liblzma-dev

# install java-8    (adds 340Mb)
RUN install_packages default-jdk

# install python3.7 (adds 800Mb)
RUN apt-get update \
	&& apt-get dist-upgrade -y \
	&& apt-get install -y python-smbus libncursesw5-dev libgdbm-dev libc6-dev zlib1g-dev libsqlite3-dev libssl-dev openssl libffi-dev

ENV PYTHON_VERSION="3.7.1"
RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz \
	&& tar xvf Python-${PYTHON_VERSION}.tar.xz \
	&& rm Python-${PYTHON_VERSION}.tar.xz \
	&& cd Python-${PYTHON_VERSION} \
	&& ./configure --enable-optimizations \
	&& make install \
	&& make clean

RUN install_packages python-pkg-resources


# install gcloud tools
RUN python3 -m pip install --upgrade pip

RUN wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-286.0.0-linux-x86_64.tar.gz
RUN tar xzf google-cloud-sdk-286.0.0-linux-x86_64.tar.gz && rm google-cloud-sdk-286.0.0-linux-x86_64.tar.gz
RUN /google-cloud-sdk/install.sh -q

# python packages
RUN python3 -m pip install --upgrade gsutil

# install GCS connector using the same steps as in https://raw.githubusercontent.com/broadinstitute/install-gcs-connector/master/install_gcs_connector.py
# assumes ~/.config/gcloud/application_default_credentials.json will be mounted into the docker container
RUN python3 -m pip install hail
COPY spark-defaults.conf /usr/local/lib/python3.7/site-packages/pyspark/conf/spark-defaults.conf
RUN wget https://repo1.maven.org/maven2/com/google/cloud/bigdataoss/gcs-connector/hadoop2-1.9.17/gcs-connector-hadoop2-1.9.17-shaded.jar -O /usr/local/lib/python3.7/site-packages/pyspark/jars/gcs-connector-hadoop2-1.9.17-shaded.jar

# install htslib
ENV SAMTOOLS_VERSION="1.9"
RUN wget https://github.com/samtools/htslib/releases/download/${SAMTOOLS_VERSION}/htslib-${SAMTOOLS_VERSION}.tar.bz2 \
	&& tar xjf htslib-${SAMTOOLS_VERSION}.tar.bz2 \
	&& rm htslib-${SAMTOOLS_VERSION}.tar.bz2 \
	&& cd htslib-${SAMTOOLS_VERSION} \
	&& ./configure \
	&& make \
	&& make install \
	&& make clean

# install VEP dependencies
RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm && chmod +x /usr/bin/cpanm
ENV VEP_VERSION="99"
RUN wget https://github.com/Ensembl/ensembl-vep/archive/release/${VEP_VERSION}.zip \
    && unzip ${VEP_VERSION}.zip \
    && rm ${VEP_VERSION}.zip

RUN /usr/bin/cpanm --notest Module::Build
RUN /usr/bin/cpanm --notest Set::IntervalTree
RUN /usr/bin/cpanm --notest PerlIO::gzip
RUN /usr/bin/cpanm --notest DBI
RUN /usr/bin/cpanm --notest CGI
RUN /usr/bin/cpanm --notest JSON
RUN /usr/bin/cpanm --notest Try::Tiny
# LoFTEE dependencies
RUN /usr/bin/cpanm --notest DBD::SQLite
RUN /usr/bin/cpanm --notest  List::MoreUtils

# install VEP
RUN cd /ensembl-vep-release-${VEP_VERSION} && perl INSTALL.pl -a ap -n -l -g all
RUN ln -s /ensembl-vep-release-${VEP_VERSION}/vep /vep

# clone and hail-elasticsearch-pipelines repo
RUN git clone https://github.com/broadinstitute/hail-elasticsearch-pipelines.git
RUN cd hail-elasticsearch-pipelines
RUN python3 -m pip install -r /hail-elasticsearch-pipelines/luigi_pipeline/requirements.txt

COPY vep-GRCh37.json /
COPY vep-GRCh38.json /

COPY bashrc /root/.bashrc
COPY gitconfig /root/.gitconfig

ENV PATH=/usr/local/lib/python3.7/site-packages/pyspark/bin:/google-cloud-sdk/bin:$PATH
ENV PYTHONPATH=".:/hail-elasticsearch-pipelines:/hail-elasticsearch-pipelines/luigi_pipeline"

COPY entrypoint.sh /

WORKDIR /

CMD [ "/entrypoint.sh" ]
