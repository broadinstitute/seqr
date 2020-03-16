#!/usr/bin/env bash

cd /seqr

nohup gunicorn -w $GUNICORN_WORKER_THREADS -c gunicorn_config.py wsgi:application |& stdbuf -o0 grep -v curl |& tee /var/log/gunicorn.log &
