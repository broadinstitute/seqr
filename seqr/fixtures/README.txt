Test fixtures in this dir provide data for seqr unit tests (documented at: https://docs.djangoproject.com/en/1.10/howto/initial-data/)

Commands used to generate fixtures:

python manage.py dumpdata seqr --format json --indent 4 > seqr/fixtures/1kg_project.json
python manage.py dumpdata auth --format json --indent 4 > seqr/fixtures/users.json
