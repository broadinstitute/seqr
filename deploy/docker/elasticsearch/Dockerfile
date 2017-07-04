FROM openjdk:8-jdk

# install commmon utilities
RUN apt-get update \
    && apt-get install -y lsof apt-utils wget curl xterm vim emacs nano less

RUN useradd -ms /bin/bash elasticsearch

RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.4.3.tar.gz \
  && tar xzf /usr/local/elasticsearch-5.4.3.tar.gz \
  && rm /usr/local/elasticsearch-5.4.3.tar.gz \
  && chown -R elasticsearch /usr/local/elasticsearch-5.4.3

EXPOSE 30001

COPY elasticsearch.yml /usr/local/elasticsearch-5.4.3/config/elasticsearch.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
