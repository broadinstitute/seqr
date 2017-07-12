FROM openjdk:8-jdk

#ENV ELASTICSEARCH_VERSION="6.0.0-alpha2"
ENV ELASTICSEARCH_VERSION="5.4.3"

# install commmon utilities
RUN apt-get update \
    && apt-get install -y lsof apt-utils wget curl xterm vim emacs nano less

RUN useradd -ms /bin/bash elasticsearch

RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && tar xzf /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && rm /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz \
  && chown -R elasticsearch /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}

ARG ELASTICSEARCH_PORT
ENV ELASTICSEARCH_PORT=$ELASTICSEARCH_PORT

EXPOSE $ELASTICSEARCH_PORT

#COPY elasticsearch.yml /usr/local/elasticsearch-${ELASTICSEARCH_VERSION}/config/elasticsearch.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
