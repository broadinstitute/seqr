FROM alpine:3.8

MAINTAINER MacArthur Lab

# install dependencies and utililties
RUN apk add --update nodejs shadow bash curl less

# install java
RUN apk add --no-cache openjdk8
ENV JAVA_HOME /usr/lib/jvm/java-1.8-openjdk
ENV PATH $PATH:/usr/lib/jvm/java-1.8-openjdk/jre/bin:/usr/lib/jvm/java-1.8-openjdk/bin

#ENV ELASTICSEARCH_VERSION="6.3.2"
ENV ELASTICSEARCH_VERSION="5.4.3"

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

