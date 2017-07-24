FROM openjdk:8-jdk

MAINTAINER MacArthur Lab

# install commmon utilities
RUN apt-get update \
    && apt-get install -y apt-utils wget curl xterm vim emacs nano less git bzip2 \
    && TERM=xterm

RUN apt-get install -y postgresql postgresql-client

RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py

# install gsutil from https://cloud.google.com/storage/docs/gsutil_install#linux
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

# Install hail
RUN cd /usr/local \
    && wget -nv http://d3kbcqa49mib13.cloudfront.net/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

RUN apt-get update && apt-get install -y g++ cmake python-pip python-dev

RUN git clone https://github.com/hail-is/hail.git \
    && cd hail \
    && git checkout bw2_elasticsearch_exporter \
    && ls

RUN pip install --upgrade jupyter

RUN cd /hail && ./gradlew -Dspark.version=2.0.2 shadowJar archiveZip
#RUN cd /hail \
#    && ./gradlew -Dspark.version=2.0.2 installDist \
#    && rm ./build/install/hail/lib/asm-3.1.jar

WORKDIR /seqr

# install seqr dependencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/requirements.txt \
    && pip install --upgrade -r requirements.txt

COPY shared/config/*.py /seqr_settings/

ENV PYTHONPATH=/seqr:/seqr_settings

COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/bashrc /root/.bashrc

COPY pipeline-runner/bashrc_custom /root/.bashrc_custom
COPY pipeline-runner/entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
