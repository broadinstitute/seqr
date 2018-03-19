FROM openjdk:8-jdk

#ENV KIBANA_VERSION="6.0.0"
ENV KIBANA_VERSION="5.6.3"

# install commmon utilities
RUN apt-get update \
    && apt-get install -y lsof apt-utils wget curl xterm vim emacs nano less

RUN useradd -ms /bin/bash kibana

RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/kibana/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && tar xzf /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && rm /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && chown -R kibana /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64

ARG KIBANA_SERVICE_PORT
ENV KIBANA_SERVICE_PORT=$KIBANA_SERVICE_PORT

EXPOSE $KIBANA_SERVICE_PORT

COPY kibana.yml /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64/config/kibana.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
