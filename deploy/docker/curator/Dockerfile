FROM debian:stable

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -s https://packages.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor | tee /etc/apt/trusted.gpg.d/curator-stable.gpg
COPY curator.list /etc/apt/sources.list.d/curator.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    elasticsearch-curator \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
