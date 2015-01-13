command = 'gunicorn'
bind = '0.0.0.0:8001'
workers = 3
user = '<%= @user %>'
loglevel = 'info'
pythonpath='<%= @xbrowse_repo_dir %>'
errorlog = '/var/log/gunicorn-error.log'
accesslog = '/var/log/gunicorn-access.log'

# # log to stdout
# errorlog = '-'  
# accesslog = '-'