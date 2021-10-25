FROM python:3.7-slim-bullseye

LABEL maintainer="Broad TGG"

# install commmon utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    bzip2 \
    curl \
    emacs \
    git \
    htop \
    less \
    nano \
    xterm \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install dev dependencies for react, javascript development. These are not needed at runtime.
RUN apt-get update \
    && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
    && apt-get install -y --no-install-recommends \
        nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install database clients for debugging
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-client \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install gcloud tools
RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && curl https://sdk.cloud.google.com | bash \
    && apt-get update && apt-get install -y \
        gcc \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install gsutil

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update && apt-get install -y \
        google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl \
    && chmod +x ./kubectl \
    && mv ./kubectl /usr/local/bin/kubectl


# DISABLE_CACHE work-around to force git pull on every docker build, based on https://github.com/docker/docker/issues/1996
ARG DISABLE_CACHE=1
ARG SEQR_REPO=https://github.com/broadinstitute/seqr
ARG SEQR_GIT_BRANCH=master

# update seqr repo
RUN git clone -q --branch $SEQR_GIT_BRANCH $SEQR_REPO

WORKDIR /seqr

# install seqr dependencies
RUN pip install wheel && pip install -r requirements.txt

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT

EXPOSE $SEQR_SERVICE_PORT

ENV TERM=xterm

COPY readiness_probe /
COPY bin/*.sh /usr/local/bin/
COPY gitconfig /root/.gitconfig
COPY config/*.py ./
COPY bashrc /root/.bashrc

COPY entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
