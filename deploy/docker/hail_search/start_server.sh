#!/usr/bin/env bash
gunicorn hail_search.web_app:init_web_app -c /gunicorn_config.py
