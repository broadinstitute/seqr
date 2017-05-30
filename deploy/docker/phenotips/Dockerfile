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
#ARG PT_VERSION="1.3"

# dev utilities
RUN apt-get update
RUN apt-get install -y xterm vim emacs nano
RUN apt-get install -y postgresql postgresql-client


RUN wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip
RUN unzip phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

WORKDIR /phenotips-standalone-${PT_VERSION}

RUN wget https://jdbc.postgresql.org/download/postgresql-42.1.1.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-42.1.1.jar

# just use the default xwiki for now - when using postgres JDBC connection url, setting xwiki.db=xwiki in xwiki.cfg
# causes errors (http://lists.xwiki.org/pipermail/users/2011-May/019918.html)
COPY config/${PT_VERSION}/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg
COPY config/${PT_VERSION}/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

# NOTE: init/extension directory and init_phenotips_db.sql were exported from a
#   a newly-installed PhenoTips instance after it was manually initialized through the UI.
#
#   Copying the extension directory like this, and later loading init_phenotips_db.sql into
#   'xwiki' (eg. by running psql -U postgres xwiki -f init_phenotips_db.sql ) allows these
#   initialization steps to be skipped.
RUN rm -rf data/extension data/jobs
COPY init/${PT_VERSION}/extension ./data/extension
COPY init/${PT_VERSION}/jobs ./data/jobs
COPY init/${PT_VERSION}/init_phenotips_db.sql /

# jetty port
EXPOSE 8080

# debug port, if debugging is on.
# EXPOSE 5050

COPY start_in_background.sh .
COPY bashrc /root/.bashrc
COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
