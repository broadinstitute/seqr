FROM python:3.7-slim-bullseye

LABEL maintainer="Broad TGG"

# install commmon utilities, database clients for debugging
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    bzip2 \
    curl \
    emacs \
    gcc \
    git \
    gnupg \
    htop \
    less \
    libc6-dev \
    libpq-dev \
    nano \
    xterm \
    postgresql \
    postgresql-client \
    procps \
    redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install gcloud tools
RUN echo "deb http://packages.cloud.google.com/apt cloud-sdk-bullseye main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update && apt-get install -y --no-install-recommends \
        google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# DISABLE_CACHE work-around to force git pull on every docker build, based on https://github.com/docker/docker/issues/1996
ARG DISABLE_CACHE=1
ARG SEQR_REPO=https://github.com/broadinstitute/seqr
ARG SEQR_GIT_BRANCH=master

# update seqr repo
RUN git clone -q --branch $SEQR_GIT_BRANCH $SEQR_REPO

WORKDIR /seqr

# install seqr dependencies
RUN pip install --no-cache-dir wheel && pip install --no-cache-dir -r requirements.txt

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

CMD [ "/entrypoint.sh" ]
