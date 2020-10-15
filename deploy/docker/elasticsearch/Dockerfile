FROM openjdk:8-jdk

LABEL maintainer="Broad TGG"

ENV ELASTICSEARCH_VERSION="6.3.2"

# install commmon utilities
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl less \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# create 'elasticsearch' user
RUN useradd -ms /bin/bash elasticsearch

# download and install
RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && tar xzf /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && rm /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && chown -R elasticsearch /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}

# install plugins
RUN /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}/bin/elasticsearch-plugin install -b repository-gcs

# environment and config
ARG ELASTICSEARCH_SERVICE_PORT
ENV ELASTICSEARCH_SERVICE_PORT=$ELASTICSEARCH_SERVICE_PORT

EXPOSE $ELASTICSEARCH_SERVICE_PORT

COPY elasticsearch.yml /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}/config/elasticsearch.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]

