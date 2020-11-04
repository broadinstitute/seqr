#!/usr/bin/env bash

set -ex

# Due to travis filesystem issues, need to explicitly grant permissions for the volume mount from the container
# This is not required to use docker-compose locally, only for testing
docker-compose up -d elasticsearch
docker-compose exec elasticsearch chmod 777 ./data

docker-compose up -d seqr
docker-compose logs postgres
docker-compose logs elasticsearch
docker-compose logs redis
docker-compose exec seqr curl elasticsearch:9200
sleep 30
docker-compose logs seqr
echo -ne 'testpassword\n' docker-compose exec seqr python manage.py createsuperuser --username test --email test@test.com
