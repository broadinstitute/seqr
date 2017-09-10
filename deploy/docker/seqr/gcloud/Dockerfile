FROM debian:jessie

MAINTAINER MacArthur Lab

# install commmon utilities
RUN apt-get update \
    && apt-get install -y apt-utils wget curl xterm vim emacs nano less git bzip2


# install dependencies of generate_pedigree_images command which generates static images using HaploPainter.pl
RUN apt-get install -y perl build-essential libcairo2-dev libgtk2.0-dev libglib2.0-bin libglib2.0-0 libpango1.0-dev

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest Cairo DBI Gtk2 Tk Sort::Naturally

# install utilities for accessing the database, debugging, etc.
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6 \
    && echo "deb http://repo.mongodb.org/apt/debian jessie/mongodb-org/3.4 main" | tee /etc/apt/sources.list.d/mongodb-org-3.4.list \
    && apt-get update \
    && apt-get install -y mongodb-org-tools mongodb-org-shell

RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' >> /etc/apt/sources.list.d/postgresql.list \
    && wget --no-check-certificate -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O- | apt-key add - \
    && apt-get update \
    && apt-get install -y postgresql postgresql-client

RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py

RUN GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s) \
    && echo "deb http://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y gcsfuse \
    && mkdir /seqr-mounted-bucket


# install gsutil from https://cloud.google.com/storage/docs/gsutil_install#linux
ENV TERM=xterm

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && curl https://sdk.cloud.google.com | bash \
    && apt-get install -y gcc python-dev python-setuptools libffi-dev libssl-dev \
    && pip install gsutil

RUN CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y google-cloud-sdk

RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl \
    && chmod +x ./kubectl \
    && mv ./kubectl /usr/local/bin/kubectl


# update seqr repo
# DISABLE_CACHE work-around to force git pull on every docker build, based on https://github.com/docker/docker/issues/1996
ARG DISABLE_CACHE=1

RUN git clone -q https://github.com/macarthur-lab/seqr && cd seqr && git checkout bw2_loading_using_hail

WORKDIR /seqr

# install seqr dependencies
RUN pip install --upgrade pip gunicorn \
    && pip install --upgrade -r requirements.txt

COPY shared/config/*.py /seqr_settings/

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT

EXPOSE $SEQR_SERVICE_PORT

ENV PYTHONPATH=/seqr:/seqr_settings

COPY shared/readiness_probe /
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bashrc /root/.bashrc

COPY gcloud/bashrc_custom /root/.bashrc_custom
COPY gcloud/entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
