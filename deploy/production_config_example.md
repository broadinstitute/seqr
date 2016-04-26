gunicorn command:
`/usr/local/bin/gunicorn -c gunicorn_config.py wsgi:application -g gunicorn -u gunicorn`

The `gunicorn_config.py` file:

```
bind = '0.0.0.0:8001'
workers = 8
loglevel = 'info'
pythonpath='/local/code/xbrowse'
errorlog = '/var/log/gunicorn-error.log'
accesslog = '/var/log/gunicorn-access.log'
```

The `/etc/nginx/nginx.conf` file:

```
user  nginx;
worker_processes  1;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    keepalive_timeout  65;
    proxy_read_timeout          3600;

    include /etc/nginx/conf.d/*.conf;
}
```

The `/etc/nginx/conf.d/default.conf`

```
server {

    listen 80;

    return 301 https://seqr.broadinstitute.org$request_uri;
}


server {

    server_name  seqr.broadinstitute.org;

    # Based on nginx / SSL tutorial at http://bit.ly/1z4r9D8
    listen 443 ssl;

    ssl_certificate /location/of/seqr_broadinstitute_org_cert.pem;
    ssl_certificate_key /location/of/seqr.broadinstitute.org.key;

    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2; 
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK;

    # Add HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";

    location /static/ {
	      alias /local/code/xbrowse/static/;
	      index index.html;
        autoindex on;
    }

    location /{
            proxy_pass http://localhost:8001;
            proxy_set_header X-Forwarded-Host $server_name;
            proxy_set_header X-Real-IP $remote_addr;
            add_header P3P 'CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV"';
    }
}
```

