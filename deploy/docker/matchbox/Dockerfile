FROM maven:3.5.0-jdk-8

MAINTAINER MacArthur Lab

ADD settings.xml /root/.m2/settings.xml
ADD entrypoint.sh  /root/bin/entrypoint.sh

#first get Exomiser built in the local maven for matchbox to import in
#---------------------------------------------------------------------------

RUN git clone -b development https://github.com/exomiser/Exomiser
WORKDIR Exomiser
RUN mvn clean install package

#now matchbox (and it will see Exomisor in local maven repo
#---------------------------------------------------------------------------

RUN git clone https://github.com/macarthur-lab/matchbox
WORKDIR matchbox
RUN mvn -Dmaven.test.skip=true clean install package

EXPOSE 9020

CMD ["/root/bin/entrypoint.sh"]
