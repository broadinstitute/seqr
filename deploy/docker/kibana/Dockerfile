FROM openjdk:8-jre-alpine

MAINTAINER MacArthur Lab

#ENV KIBANA_VERSION="6.3.2"
ENV KIBANA_VERSION="5.4.3"

# create user 'kibana'
RUN apk add --update nodejs shadow bash \
  && useradd -ms /bin/bash kibana

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
