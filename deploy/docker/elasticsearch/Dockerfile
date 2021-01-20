FROM docker.elastic.co/elasticsearch/elasticsearch:7.8.1

LABEL maintainer="Broad TGG"

ENV ELASTICSEARCH_VERSION="7.8.1"

# install plugins
RUN bin/elasticsearch-plugin install --batch repository-gcs

# environment and config
ARG ELASTICSEARCH_SERVICE_PORT
ENV ELASTICSEARCH_SERVICE_PORT=$ELASTICSEARCH_SERVICE_PORT

EXPOSE $ELASTICSEARCH_SERVICE_PORT

COPY --chown=elasticsearch:elasticsearch sysctl.conf /etc/sysctl.conf

COPY --chown=elasticsearch:elasticsearch elasticsearch.yml /usr/share/elasticsearch/config/

