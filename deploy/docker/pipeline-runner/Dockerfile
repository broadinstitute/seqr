FROM openjdk:8-jdk

MAINTAINER MacArthur Lab

# install commmon utilities
RUN apt-get update \
    && apt-get install -y apt-utils wget curl xterm vim emacs nano less git htop bzip2 g++ cmake  \
    && TERM=xterm

RUN apt-get install -y postgresql postgresql-client

RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py

# install jupyter
RUN pip install --upgrade jupyter

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

# install picard
RUN mkdir /picard \
    && cd /picard \
    && wget https://github.com/broadinstitute/picard/releases/download/2.15.0/picard.jar

# download LiftoverChain files
RUN mkdir -p /reference-data \
    && cd /reference-data \
    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz \
    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz

# install VEP - steps taken from gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh
RUN mkdir -p /vep/homo_sapiens \
    && gsutil -m cp -r gs://hail-common/vep/vep/loftee /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/ensembl-tools-release-85 /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/GRCh38/loftee_data /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/Plugins /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh38 /vep/homo_sapiens/

RUN gsutil cp gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-gcloud.properties /vep/vep-gcloud.properties \
    && gsutil cp gs://hail-common/vep/htslib/* /usr/bin/ \
    && gsutil cp gs://hail-common/vep/samtools /usr/bin/ \
    && chmod a+rx  /usr/bin/tabix /usr/bin/bgzip /usr/bin/htsfile /usr/bin/samtools

RUN ln -s /vep/ensembl-tools-release-85/scripts/variant_effect_predictor /vep/variant_effect_predictor \
    && gsutil cp gs://hail-common/vep/vep/GRCh38/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_vcf.sh  \
    && chmod a+rx /vep/run_hail_vep85_vcf.sh

RUN wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest CGI DBI JSON

# run VEP on the 1-variant VCF to create fasta.index file -- caution do not make fasta.index file writeable afterwards!
RUN gsutil cp gs://hail-common/vep/vep/1var.vcf /vep  \
    && /vep/run_hail_vep85_vcf.sh /vep/1var.vcf

# install hail
RUN cd /usr/local \
    && wget -nv http://apache.cs.utah.edu/spark/spark-2.0.2/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

RUN cd / \
    && git clone --branch 0.1 https://github.com/broadinstitute/hail.git \
    && cd /hail \
    && ./gradlew -Dspark.version=2.0.2 shadowJar

#RUN cd /hail \
#    && ./gradlew -Dspark.version=2.0.2 installDist \
#    && rm ./build/install/hail/lib/asm-3.1.jar

WORKDIR /seqr

# install seqr dependencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/requirements.txt \
    && pip install --upgrade -r requirements.txt

COPY shared/config/*.py /seqr_settings/

RUN cd / \
    && git clone https://github.com/macarthur-lab/hail-elasticsearch-pipelines.git


ENV PYTHONPATH="$PYTHONPATH:/seqr:/seqr_settings"

COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/bashrc /root/.bashrc

COPY bashrc_custom /root/.bashrc_custom
COPY entrypoint.sh /

WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
