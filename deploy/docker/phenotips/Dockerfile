# Creates a PhenoTips instance that's configured to use a postgres database.
# This Dockerfile is based on https://github.com/meatcar/docker-phenotips/blob/master/Dockerfile

FROM bitnami/minideb:stretch

MAINTAINER MacArthur Lab

# PhenoTips version to install
ENV PT_VERSION="1.2.6"
#ENV PT_VERSION="1.3.4"
#ENV PT_VERSION="1.4-milestone-1"

RUN install_packages default-jdk

# install common utilities
RUN install_packages curl emacs nano less htop wget unzip

# install postgres client
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-client

# download and install phenotips
RUN wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip \
    && unzip phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

WORKDIR /phenotips-standalone-${PT_VERSION}

# install postgres driver into phenotips
RUN wget https://jdbc.postgresql.org/download/postgresql-42.1.4.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-42.1.4.jar

# update phenotips config
COPY config/${PT_VERSION}/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg
COPY config/${PT_VERSION}/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

# by default, installing phenotips requires manual interation with a web UI at the end for it to set up the final
#   phenotips UI. To fully automate the installation, we did these manual steps and then saved the resulting
#   init/${PT_VERSION}/extension directory + the postgres database contents to init/${PT_VERSION}/init_phenotips_db.sql
#
#   Then, for a new install, if we copy init/${PT_VERSION}/extension into the installation directory, and restore
#   init_phenotips_db.sql, it causes phenotips to skip the final UI installation wizard and go directly to a fully
#   initialized state.
RUN rm -rf data/extension data/jobs
COPY init/${PT_VERSION}/extension ./data/extension
COPY init/${PT_VERSION}/jobs ./data/jobs
COPY init/${PT_VERSION}/init_phenotips_db.sql /

# jetty port
ARG PHENOTIPS_SERVICE_PORT
ENV PHENOTIPS_SERVICE_PORT=$PHENOTIPS_SERVICE_PORT
EXPOSE $PHENOTIPS_SERVICE_PORT

# debug port, if debugging is on.
# EXPOSE 5050

COPY readiness_probe /
COPY start_in_background.sh .
COPY bashrc /root/.bashrc
COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
