#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

cd /seqr

git pull
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input


cd /seqr_settings

# launch django dev server in background
gunicorn -c gunicorn_config.py wsgi:application &

# sleep to keep image running even if servers are killed / restarted during development
sleep 1000000000000

