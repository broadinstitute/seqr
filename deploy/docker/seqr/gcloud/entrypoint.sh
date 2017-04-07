#!/usr/bin/env bash

env

gunicorn -c gunicorn_config.py wsgi:application --timeout 3600
