FROM alpine:3.8

MAINTAINER MacArthur Lab

# install dependencies and utililties
RUN apk add --update nodejs shadow bash curl less

# install java
RUN apk add --no-cache openjdk8
ENV JAVA_HOME /usr/lib/jvm/java-1.8-openjdk
ENV PATH $PATH:/usr/lib/jvm/java-1.8-openjdk/jre/bin:/usr/lib/jvm/java-1.8-openjdk/bin

ENV KIBANA_VERSION="6.3.2"
#ENV KIBANA_VERSION="5.4.3"

# create 'kibana' user
RUN useradd -ms /bin/bash kibana

# download and install kibana
RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/kibana/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && tar xzf /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && rm /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && chown -R kibana /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64

# fix node installation (https://github.com/elastic/kibana/issues/17015)
ENV KIBANA_DIR=/usr/local/kibana-${KIBANA_VERSION}-linux-x86_64
RUN rm -rf ${KIBANA_DIR}/node \
  && mkdir -p ${KIBANA_DIR}/node/bin \
  && ln -s /usr/bin/node ${KIBANA_DIR}/node/bin/node

# environment and config
ARG KIBANA_SERVICE_PORT
ENV KIBANA_SERVICE_PORT=$KIBANA_SERVICE_PORT

EXPOSE $KIBANA_SERVICE_PORT

COPY kibana.yml ${KIBANA_DIR}/config/kibana.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
