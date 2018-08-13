FROM openjdk:8-jdk

MAINTAINER MacArthur Lab

# install commmon utilities
RUN apt-get update \
    && apt-get install -y apt-utils wget curl xterm vim emacs nano less htop bzip2 g++ cmake --fix-missing \
    && TERM=xterm

RUN apt-get install -y postgresql postgresql-client

RUN apt-get install -y python-dev \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py

# install ipython/jupyter notebooks
RUN pip install --upgrade jupyter

# install gsutil and other gcloud utils
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
#RUN mkdir /picard \
#    && cd /picard \
#    && wget https://github.com/broadinstitute/picard/releases/download/2.15.0/picard.jar

# download LiftoverChain files
#RUN mkdir -p /reference-data \
#    && cd /reference-data \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz \
#    && wget http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz

# install VEP - steps taken from gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-init.sh and gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-init.sh
RUN mkdir -p /vep/homo_sapiens /vep/loftee_data_grch37 /vep/loftee_data_grch38 \
    && gsutil -m cp -r gs://hail-common/vep/vep/loftee /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/ensembl-tools-release-85 /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/GRCh37/loftee_data /vep/loftee_data_grch37  \
    && gsutil -m cp -r gs://hail-common/vep/vep/GRCh38/loftee_data /vep/loftee_data_grch38  \
    && gsutil -m cp -r gs://hail-common/vep/vep/Plugins /vep  \
    && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh37 /vep/homo_sapiens/ \
    && gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/85_GRCh38 /vep/homo_sapiens/

# install perl v5.20  (hail/VEP doesn't currently work with newer versions of perl)
RUN apt-get remove -y perl \
    && apt-get install -y perlbrew patch \
    && perlbrew init \
    && perlbrew install -j 5 --notest perl-5.20.3 \
    && perlbrew switch perl-5.20.3 \
    && gsutil -m cp -r gs://hail-common/vep/perl-JSON/*  /root/perl5/perlbrew/perls/perl-5.20.3/lib/site_perl/5.20.3/x86_64-linux/   \
    && gsutil -m cp -r gs://hail-common/vep/perl-SQLITE/*  /root/perl5/perlbrew/perls/perl-5.20.3/lib/site_perl/5.20.3/x86_64-linux/

RUN apt-get install -y cpanminus \
    && cpanm --notest CGI DBI JSON

COPY vep-gcloud-grch37.properties /vep
COPY vep-gcloud-grch38.properties /vep

# gsutil cp gs://hail-common/vep/vep/GRCh37/vep85-GRCh37-gcloud.properties /vep/vep-gcloud-grch37.properties \
# gsutil cp gs://hail-common/vep/vep/GRCh38/vep85-GRCh38-gcloud.properties /vep/vep-gcloud-grch38.properties \
RUN gsutil cp gs://hail-common/vep/htslib/* /usr/bin/ \
    && gsutil cp gs://hail-common/vep/samtools /usr/bin/ \
    && chmod a+rx  /usr/bin/tabix /usr/bin/bgzip /usr/bin/htsfile /usr/bin/samtools

RUN ln -s /vep/ensembl-tools-release-85/scripts/variant_effect_predictor /vep/variant_effect_predictor \
    && gsutil cp gs://hail-common/vep/vep/GRCh37/run_hail_vep85_GRCh37_vcf.sh /vep/run_hail_vep85_GRCh37_vcf.sh  \
    && gsutil cp gs://hail-common/vep/vep/GRCh38/run_hail_vep85_GRCh38_vcf.sh /vep/run_hail_vep85_GRCh38_vcf.sh  \
    && chmod a+rx /vep/run_hail_vep85_GRCh37_vcf.sh \
    && chmod a+rx /vep/run_hail_vep85_GRCh38_vcf.sh

# run VEP on the 1-variant VCF to create fasta.index file -- caution do not make fasta.index file writeable afterwards!
RUN gsutil cp gs://hail-common/vep/vep/1var.vcf /vep  \
    && /vep/run_hail_vep85_GRCh37_vcf.sh /vep/1var.vcf \
    && /vep/run_hail_vep85_GRCh38_vcf.sh /vep/1var.vcf

# install hail
RUN cd /usr/local \
    && wget -nv https://archive.apache.org/dist/spark/spark-2.0.2/spark-2.0.2-bin-hadoop2.7.tgz \
    && tar xzf /usr/local/spark-2.0.2-bin-hadoop2.7.tgz

RUN pip install decorator==4.2.1    # fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468

RUN wget https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-latest-hadoop2.jar -O /usr/local/spark-2.0.2-bin-hadoop2.7/jars/gcs-connector-latest-hadoop2.jar

RUN cd / \
    && apt-get install -y git \
    && git clone --branch 0.1 https://github.com/broadinstitute/hail.git \
    && cd /hail \
    && ./gradlew -Dspark.version=2.0.2 shadowJar archiveZip


#RUN cd /hail \
#    && ./gradlew -Dspark.version=2.0.2 installDist \
#    && rm ./build/install/hail/lib/asm-3.1.jar

RUN cd / && git clone https://github.com/macarthur-lab/seqr.git
RUN cd / && git clone https://github.com/macarthur-lab/hail-elasticsearch-pipelines.git

WORKDIR /seqr

# install seqr dependencies
RUN wget -N https://raw.githubusercontent.com/macarthur-lab/seqr/master/requirements.txt \
    && pip install --upgrade -r requirements.txt

COPY shared/config/*.py /seqr_settings/


ENV PYTHONPATH="$PYTHONPATH:/seqr:/seqr_settings"

COPY shared/gitconfig /root/.gitconfig
COPY shared/config/*.py /seqr_settings/
COPY shared/bin/*.sh /usr/local/bin/
COPY shared/bashrc /root/.bashrc

COPY bashrc_custom /root/.bashrc_custom
COPY entrypoint.sh /

COPY core-site.xml /usr/local/spark-2.0.2-bin-hadoop2.7/conf/


WORKDIR /seqr

CMD [ "/entrypoint.sh" ]
