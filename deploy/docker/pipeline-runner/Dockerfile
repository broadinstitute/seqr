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

RUN python3 -m pip install --upgrade pip

# python packages
RUN python3 -m pip install hail

# install gcs connector
RUN python3 -m pip install git+https://github.com/bw2/hail-utils.git

#RUN wget https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop2-latest.jar -o $(python3 -c "from pyspark.find_spark_home import _find_spark_home; print(_find_spark_home())")/jars/gcs-connector-hadoop2-latest.jar

RUN python3 -m pip install ipython

#hl.hadoop_exists("gs://seqr-datasets/GRCh37/1kg/1kg.mt")

COPY entrypoint.sh /
CMD [ "/entrypoint.sh" ]
