FROM postgres:9.6.2

MAINTAINER MacArthur Lab

# utils for debugging
RUN apt-get update \
    && apt-get install -y xterm less vim emacs nano

COPY bashrc /root/.bashrc


#COPY 001_init.sql /docker-entrypoint-initdb.d/
#COPY 002_init.sh  /docker-entrypoint-initdb.d/
COPY postgresql.conf  /root/postgresql.conf

COPY postgresql.conf  /var/lib/postgresql/data/postgresql.conf
RUN chmod 444 /var/lib/postgresql/data/postgresql.conf
