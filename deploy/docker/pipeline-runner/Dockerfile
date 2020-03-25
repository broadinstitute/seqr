FROM bitnami/minideb:stretch

MAINTAINER MacArthur Lab

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

# install gcloud tools
RUN python3 -m pip install --upgrade pip

RUN python3 -m pip install gsutil
RUN wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-286.0.0-linux-x86_64.tar.gz
RUN tar xzf google-cloud-sdk-286.0.0-linux-x86_64.tar.gz && rm google-cloud-sdk-286.0.0-linux-x86_64.tar.gz
RUN /google-cloud-sdk/install.sh -q

# python packages
RUN python3 -m pip install hail
RUN python3 -m pip install ipython

COPY entrypoint.sh /
CMD [ "/entrypoint.sh" ]
