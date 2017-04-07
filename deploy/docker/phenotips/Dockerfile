# Creates a PhenoTips instance that's configured to use a postgres database on localhost:5432 (the default postges port)
#
# That postgres instance must already contain an empty database named 'xwiki', as well as a
# 'postgres' database user as specified in the hibernate.cfg.xml config file
#
# NOTE: this Dockerfile is based on https://github.com/meatcar/docker-phenotips/blob/master/Dockerfile
#

FROM java:8

MAINTAINER MacArthur Lab

ARG PT_VERSION="1.2.6"

#RUN apt-get update && apt-get -y install unzip

RUN wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip
RUN unzip phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

WORKDIR /phenotips-standalone-${PT_VERSION}

RUN wget https://jdbc.postgresql.org/download/postgresql-9.4.1212.jre6.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-9.4-1206-jdbc4.jar

# when using postgres JDBC connection url, setting xwiki.db=xwiki in xwiki.cfg causes errors (http://lists.xwiki.org/pipermail/users/2011-May/019918.html)
# COPY config/xwiki.cfg ./webapps/phenotips/WEB-INF/classes/xwiki.cfg
# COPY config/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg

#COPY config/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/classes/hibernate.cfg.xml
COPY config/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

# RUN apt-get update \
#    && apt-get install -y nano \
#    && echo "export TERM=xterm" >> ~/.bashrc

RUN rm -rf data/extension/

COPY extension ./data/extension

# jetty port
EXPOSE 8080

# debug port, if on.
# EXPOSE 5050

COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
