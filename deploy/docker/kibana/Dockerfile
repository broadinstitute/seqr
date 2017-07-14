FROM openjdk:8-jdk

# "6.0.0-alpha2"
ENV KIBANA_VERSION="5.4.3"

# install commmon utilities
RUN apt-get update \
    && apt-get install -y lsof apt-utils wget curl xterm vim emacs nano less

RUN useradd -ms /bin/bash kibana

RUN cd /usr/local \
  && wget -nv https://artifacts.elastic.co/downloads/kibana/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && tar xzf /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && rm /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64.tar.gz \
  && chown -R kibana /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64

ARG KIBANA_PORT
ENV KIBANA_PORT=$KIBANA_PORT

EXPOSE $KIBANA_PORT

COPY kibana.yml /usr/local/kibana-${KIBANA_VERSION}-linux-x86_64/config/kibana.yml
COPY entrypoint.sh /

CMD [ "/entrypoint.sh" ]
