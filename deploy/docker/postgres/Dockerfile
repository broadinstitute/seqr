FROM postgres:12.3

LABEL maintainer="Broad TGG"

# install wget
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates htop less wget curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY bashrc /root/.bashrc

COPY restore_database_backup.sh /root/restore_database_backup.sh

COPY postgresql.conf /etc/postgresql/postgresql.conf

ENV PGDATA=/var/lib/postgresql/data/pgdata
