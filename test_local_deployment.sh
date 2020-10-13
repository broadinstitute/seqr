#!/usr/bin/env bash

set -ex

cp docker-compose.yml ..
cd ..
mkdir ./data
chmod +rw ./data

docker-compose up -d elasticsearch
docker-compose exec elasticsearch chmod +rw ./data
sleep 30
docker-compose logs elasticsearch

docker-compose up -d seqr
docker-compose logs postgres
docker-compose logs elasticsearch
docker-compose logs redis
docker-compose exec seqr curl elasticsearch:9200
sleep 30
docker-compose logs seqr
echo -ne 'testpassword\n' docker-compose exec seqr python manage.py createsuperuser --username test --email test@test.com
