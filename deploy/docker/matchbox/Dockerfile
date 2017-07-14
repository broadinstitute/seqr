FROM openjdk:8-jdk

RUN apt-get update
RUN apt-get install -y wget
RUN apt-get install -y git
RUN apt-get install -y maven

#installing crcmod as per google instructions to speed up download
#of supporting files from google
#---------------------------------------------------------------------------

RUN apt-get install -y python
RUN apt-get install -y gcc 
RUN apt-get install -y python-dev
RUN apt-get install -y python-setuptools
RUN /usr/bin/easy_install -U pip
RUN /usr/local/bin/pip install crcmod

MAINTAINER MacArthur Lab

ADD settings.xml /root/.m2/settings.xml
ADD entrypoint.sh  /root/bin/entrypoint.sh

env MVN=mvn

#first get Exomiser built in the local maven for matchbox to import in
#---------------------------------------------------------------------------

RUN git clone -b development https://github.com/exomiser/Exomiser
WORKDIR Exomiser
RUN $MVN clean install package

#now matchbox (and it will see Exomisor in local maven repo)
#---------------------------------------------------------------------------

RUN git clone https://github.com/macarthur-lab/matchbox
WORKDIR matchbox
RUN $MVN -Dmaven.test.skip=true clean install package

env MATCHBOX_JAR=/Exomiser/matchbox/target/matchbox-0.1.0.jar
env MATCHBOX_CONFIG_DIR=/Exomiser/matchbox/config


#Now get support data for Exomiser models (for now, cpying, switch with wget)
#-----------------------------------------------------

#----first get gsutils to interface with google
RUN wget https://storage.googleapis.com/pub/gsutil.tar.gz
RUN mkdir /root/gsutils_dir
RUN tar xfz gsutil.tar.gz -C /root/gsutils_dir
RUN rm gsutil.tar.gz
RUN export PATH=${PATH}:/root/gsutils_dir/gsutil

#----now get the data and untar it
RUN mkdir /root/reference_data
RUN /root/gsutils_dir/gsutil/gsutil -m -o GSUtil:parallel_composite_upload_threshold=150M cp gs://seqr-hail/reference_data/exomiser/data.tar.gz /root/reference_data/data.local.tar.gz
RUN tar -xvzf /root/reference_data/data.local.tar.gz --directory /root/reference_data
RUN rm /root/reference_data/data.local.tar.gz


#Now set matchbox up for deployment and copy over jar and config files
#---------------------------------------------------------------------------
WORKDIR /matchbox_deployment
RUN cp -rf $MATCHBOX_CONFIG_DIR .
RUN cp $MATCHBOX_JAR .


EXPOSE 9020

CMD ["/root/bin/entrypoint.sh"]
