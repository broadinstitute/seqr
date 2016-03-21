# script for deploying static files in production
python manage.py collectstatic --link -i 'font-awesome*' -i 'igv.css' -i 'DT_bootstrap.css' -i 'jquery-ui-1.*'
