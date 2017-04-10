#!/usr/bin/env bash

pkill -f runserver

cd /seqr

python manage.py runserver &

