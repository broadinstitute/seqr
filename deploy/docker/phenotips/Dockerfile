# Creates a PhenoTips instance that's configured to use a postgres database running on localhost.
#
# DEPENDENCIES:
#     A postgres database running on localhost, that contains an empty database named 'xwiki', owned by the 'postgres' user.
#
# NOTE:
#     This Dockerfile is based on https://github.com/meatcar/docker-phenotips/blob/master/Dockerfile
#

FROM java:8

MAINTAINER MacArthur Lab

ARG PT_VERSION="1.2.6"

# dev utilities
RUN apt-get update
RUN apt-get install -y xterm vim emacs nano
RUN apt-get install -y postgresql postgresql-client


RUN wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip
RUN unzip phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

WORKDIR /phenotips-standalone-${PT_VERSION}

RUN wget https://jdbc.postgresql.org/download/postgresql-9.4.1212.jre6.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-9.4-1206-jdbc4.jar

# just use the default xwiki for now - when using postgres JDBC connection url, setting xwiki.db=xwiki in xwiki.cfg
# causes errors (http://lists.xwiki.org/pipermail/users/2011-May/019918.html)
# COPY config/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg

COPY config/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

# NOTE: init/extension directory and init_phenotips_db.sql were exported from a
#   a newly-installed PhenoTips instance after it was manually initialized through the UI.
#
#   Copying the extension directory like this, and later loading init_phenotips_db.sql into
#   'xwiki' (eg. by running psql -U postgres xwiki -f init_phenotips_db.sql ) allows these
#   initialization steps to be skipped.
RUN rm -rf data/extension/
COPY init/extension ./data/extension

# jetty port
EXPOSE 8080

# debug port, if debugging is on.
# EXPOSE 5050

COPY bashrc /root/.bashrc
COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
