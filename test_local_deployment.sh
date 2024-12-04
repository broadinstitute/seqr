#!/usr/bin/env bash

set -ex

docker compose up -d elasticsearch

# Due to travis filesystem issues, need to explicitly grant permissions for the volume mount from the container
# This is not required to use docker compose locally, only for testing
docker compose exec -T elasticsearch chmod 777 ./data

mkdir ./data/postgres_init
cp ./deploy/postgres/initdb.sql ./data/postgres_init/initdb.sql

docker compose up -d seqr
docker compose logs postgres
docker compose logs elasticsearch
docker compose logs redis
docker compose exec -T seqr curl elasticsearch:9200
sleep 30
docker compose logs seqr
echo -ne 'testpassword\n' docker compose exec -T seqr python manage.py createsuperuser --username test --email test@test.com
