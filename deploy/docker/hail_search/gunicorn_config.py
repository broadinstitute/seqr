import os
command = 'gunicorn'
bind = f'0.0.0.0:{os.environ["HAIL_SEARCH_SERVICE_PORT"]}'
workers = 1
loglevel = 'info'
timeout = 3600   # seconds (default is 30)
accesslog = '-'
errorlog = '-'  # logs to stderr
worker_class = 'aiohttp.GunicornWebWorker'
access_log_format = '%{From}i "%r" %s %Tfs'
