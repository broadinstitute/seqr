FROM postgres:9.6.2

MAINTAINER MacArthur Lab

# install wget
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates htop less wget curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY bashrc /root/.bashrc

COPY restore_database_backup.sh /root/restore_database_backup.sh

ENV PGDATA=/var/lib/postgresql/data/pgdata
