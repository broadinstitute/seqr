#!/usr/bin/env bash

cd /seqr_settings

gunicorn -w 4 -c gunicorn_config.py wsgi:application &
