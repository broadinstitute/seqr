#!/usr/bin/env bash

cd /seqr

touch settings.py

pkill -HUP -f gunicorn