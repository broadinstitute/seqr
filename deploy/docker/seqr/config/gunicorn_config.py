command = 'gunicorn'
bind = '0.0.0.0:8000'
workers = 1
loglevel = 'info'
timeout = 3600   # seconds (default is 30)
errorlog = '-'  # logs to stderr
