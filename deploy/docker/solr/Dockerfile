FROM openjdk:8-jdk

RUN apt-get update
RUN apt-get install -y lsof

RUN useradd -ms /bin/bash solr

RUN cd /usr/local \
  && wget -nv http://archive.apache.org/dist/lucene/solr/6.4.2/solr-6.4.2.tgz \
  && tar xzf /usr/local/solr-6.4.2.tgz \
  && rm /usr/local/solr-6.4.2.tgz \
  && chown -R solr /usr/local/solr-6.4.2

EXPOSE 30002 31002

COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
