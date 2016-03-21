# script for deploying static files in production

#python manage.py collectstatic --no-input --clear --link  -i 'font-awesome*' -i 'igv.css' -i 'DT_bootstrap.css' -i 'jquery-ui-1.*'
python manage.py collectstatic --no-input --clear --link --no-post-process
