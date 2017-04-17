#!/bin/bash

echo "002_init.sh is running"

env

echo ALTER USER postgres WITH PASSWORD \'${POSTGRES_PASSWORD}\' | psql -U postgres
