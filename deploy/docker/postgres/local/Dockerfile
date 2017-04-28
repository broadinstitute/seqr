FROM postgres:9.6.2

MAINTAINER MacArthur Lab

# utilities
RUN apt-get update
RUN apt-get install -y xterm vim emacs nano

COPY bashrc /root/.bashrc

#COPY 000_init.sh  /docker-entrypoint-initdb.d/
#COPY 001_init.sql /docker-entrypoint-initdb.d/
#COPY postgresql.conf  /root/postgresql.conf

COPY postgresql.conf  /var/lib/postgresql/data/postgresql.conf
RUN chmod 444 /var/lib/postgresql/data/postgresql.conf
