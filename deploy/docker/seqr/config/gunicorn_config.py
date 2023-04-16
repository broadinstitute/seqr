command = 'gunicorn'
bind = '0.0.0.0:8000'
workers = 9  # (2 * 4 cores) + 1, as suggested in https://docs.gunicorn.org/en/stable/design.html#how-many-workers
loglevel = 'info'
timeout = 3600   # seconds (default is 30)
errorlog = '-'  # logs to stderr
