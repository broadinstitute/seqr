#!/usr/bin/env bash

cd /seqr_settings

nohup gunicorn -w 4 -c gunicorn_config.py wsgi:application |& stdbuf -o0 grep -v curl |& tee /var/log/gunicorn.log &