set -ex

docker-compose up -d seqr
docker-compose logs postgres
docker-compose logs elatsicsearch
docker-compose logs redis
docker-compose logs seqr
curl localhost:9200
docker-compose exec seqr python manage.py createsuperuser --username test --email test@test.com
