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




# install picard
#RUN mkdir /picard \
#    && cd /picard \
#    && wget https://github.com/broadinstitute/picard/releases/download/2.15.0/picard.jar

# download LiftoverChain files
#RUN mkdir -p /reference-data \
#    && cd /reference-data \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz

WORKDIR /


# install hail-elasticsearch-pipelines

RUN git clone https://github.com/macarthur-lab/hail-elasticsearch-pipelines.git


# install jupyter
RUN pip install --upgrade pip jupyter

ENV TERM=xterm
ENV PYTHONPATH="$PYTHONPATH:/seqr:/seqr_settings:/hail-elasticsearch-pipelines"

COPY shared/gitconfig /root/.gitconfig
COPY shared/bashrc /root/.bashrc

COPY shared/bashrc_custom /root/.bashrc_custom
COPY gcloud/entrypoint.sh /


WORKDIR /hail-elasticsearch-pipelines

CMD [ "/entrypoint.sh" ]
