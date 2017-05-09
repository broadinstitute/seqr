FROM postgres:9.6.2

MAINTAINER MacArthur Lab

#COPY 000_init.sh  /docker-entrypoint-initdb.d/
#COPY 001_init.sql /docker-entrypoint-initdb.d/
COPY postgresql.conf  /root/postgresql.conf

COPY restore_database_backup.sh /root/restore_database_backup.sh
RUN chmod 777 /root/restore_database_backup.sh

#COPY postgresql.conf  /var/lib/postgresql/data/postgresql.conf
#RUN chmod 444 /var/lib/postgresql/data/postgresql.conf
