FROM debian:stretch

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

#  install the packages necessary to build Python source:
RUN apt update && apt install -y --no-install-recommends build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev \
    libncursesw5-dev libsqlite3-dev tk-dev libc6-dev ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG PYTHON_MAIN_VER="3.7"
ARG PYTHON_MINOR_VER="8"
ARG PYTHON_VERSION=$PYTHON_MAIN_VER.$PYTHON_MINOR_VER

# downland and install Python from soruce code
WORKDIR /
RUN curl -O https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz \
    && tar -xf Python-$PYTHON_VERSION.tar.xz \
    && rm -f Python-$PYTHON_VERSION.tar.xz

WORKDIR /Python-$PYTHON_VERSION
RUN ./configure --enable-optimizations \
    && make -j "$(nproc)" \
    && make install

WORKDIR /
RUN rm -rf ./Python-$PYTHON_VERSION \
    && ln -s /usr/local/bin/pip$PYTHON_MAIN_VER /usr/local/bin/pip \
    && ln -s /usr/local/bin/python$PYTHON_MAIN_VER /usr/local/bin/python

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

RUN curl -L0 https://raw.github.com/miyagawa/cpanminus/master/cpanm -o /usr/bin/cpanm \
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
    && apt-get install -y --no-install-recommends \
        nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install database clients for debugging (https://www.postgresql.org/download/linux/debian/)
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && curl -L0 -o - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update && apt-get install -y \
        postgresql-12 \
        postgresql-client-12 \
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

# update seqr repo
RUN git clone -q https://github.com/broadinstitute/seqr

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
COPY config/*.py ./
COPY bashrc /root/.bashrc

COPY entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
