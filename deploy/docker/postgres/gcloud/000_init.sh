#!/bin/bash

echo "000_init.sh is running"

env

# echo ALTER USER postgres WITH PASSWORD \'${POSTGRES_PASSWORD}\' | psql -U postgres

mkdir -p /var/lib/postgresql/data
cp /root/postgresql.conf /var/lib/postgresql/data/postgresql.conf
chmod 444 /var/lib/postgresql/data/postgresql.conf
