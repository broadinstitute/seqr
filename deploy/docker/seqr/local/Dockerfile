FROM debian:jessie

MAINTAINER MacArthur Lab

RUN apt-get update \
    && apt-get install -y apt-utils wget curl xterm vim emacs nano less git

# install dependencies of generate_pedigree_images command which generates static images using HaploPainter.pl
RUN apt-get install -y perl build-essential libcairo2-dev libgtk2.0-dev libglib2.0-bin libglib2.0-0 libpango1.0-dev

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest Cairo DBI Gtk2 Tk Sort::Naturally


# install dev dependencies for react, javascript development. These are not needed at runtime.
RUN apt-get update \
    && curl -sL https://deb.nodesource.com/setup_7.x | bash - \
    && apt-get install -y nodejs

# install utilities for accessing the database, debugging, etc.
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6 \
    && echo "deb http://repo.mongodb.org/apt/debian jessie/mongodb-org/3.4 main" | tee /etc/apt/sources.list.d/mongodb-org-3.4.list \
    && apt-get update \
    && apt-get install -y mongodb-org-tools mongodb-org-shell


RUN apt-get install -y postgresql postgresql-client

RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py

# install gsutil from https://cloud.google.com/storage/docs/gsutil_install#linux
RUN export CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
    && curl https://sdk.cloud.google.com | bash \
    && apt-get install -y gcc python-dev python-setuptools libffi-dev libssl-dev \
    && pip install gsutil

RUN export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
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

# install seqr dependencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/requirements.txt \
    && pip install --upgrade pip gunicorn \
    && pip install --upgrade -r requirements.txt

# install UI depedencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/ui/package.json \
    && alias node=nodejs \
    && npm install \
    && npm install -g npm-check-updates

EXPOSE 3000
EXPOSE 8000

ENV PYTHONPATH=/seqr:/seqr_settings

COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/bashrc /root/.bashrc

COPY local/bashrc_custom /root/.bashrc_custom
COPY local/entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
