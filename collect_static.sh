# script for deploying static files in production

#python manage.py collectstatic --noinput --clear --link  -i 'font-awesome*' -i 'igv.css' -i 'DT_bootstrap.css' -i 'jquery-ui-1.*'
python2.7 manage.py collectstatic --noinput --clear --link 

