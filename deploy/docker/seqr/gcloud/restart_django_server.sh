#!/usr/bin/env bash

pkill -f gunicorn

cd /seqr_settings

gunicorn -c gunicorn_config.py wsgi:application --timeout 3600 &
