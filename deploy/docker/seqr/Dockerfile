FROM debian:jessie

MAINTAINER MacArthur Lab

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
    wget \
    xterm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# install python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python-dev \
    ca-certificates \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py \
    && pip install --upgrade pip setuptools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install dependencies of the HaploPainter.pl script used to generate static pedigree images
RUN apt-get update && apt-get install -y --no-install-recommends \
    perl \
    build-essential \
    libcairo2-dev \
    libglib2.0-bin \
    libglib2.0-0 \
    libgtk2.0-dev \
    libpango1.0-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest \
        Cairo \
        DBI \
        Gtk2 \
        Tk \
        Sort::Naturally

# install dev dependencies for react, javascript development. These are not needed at runtime.
RUN apt-get update \
    && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
    && apt-get install -y \
        nodejs

# install database clients for debugging
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' >> /etc/apt/sources.list.d/postgresql.list \
    && wget --no-check-certificate -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O- | apt-key add - \
    && apt-get update && apt-get install -y \
        postgresql \
        postgresql-client \
        libpq-dev

RUN apt-get update && apt-get install -y \
    redis-tools

# install gcloud tools
RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && curl https://sdk.cloud.google.com | bash \
    && apt-get update && apt-get install -y \
        gcc \
        python-dev \
        python-setuptools \
        libffi-dev \
        libssl-dev \
        libpq-dev \
    && pip install gsutil

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update && apt-get install -y \
        google-cloud-sdk

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl \
    && chmod +x ./kubectl \
    && mv ./kubectl /usr/local/bin/kubectl


# DISABLE_CACHE work-around to force git pull on every docker build, based on https://github.com/docker/docker/issues/1996
ARG DISABLE_CACHE=1

# update seqr repo
RUN git clone -q https://github.com/macarthur-lab/seqr

WORKDIR /seqr

# install seqr dependencies
RUN pip install -r requirements.txt

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT

EXPOSE $SEQR_SERVICE_PORT

ENV TERM=xterm

COPY readiness_probe /
COPY bin/*.sh /usr/local/bin/
COPY gitconfig /root/.gitconfig
COPY config/*.py /
COPY bashrc /root/.bashrc

COPY entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
