#!/usr/bin/env bash

set -x

env

if [ "$DEPLOY_TO" = 'local' ]
then
    # wait for drive to be mounted
    while [ ! -f /seqr/manage.py ]
    do
        echo "Error: /seqr/manage.py doesn't exist. It may just not have been mounted yet..."

        sleep 5
    done

    ls -la1 /seqr/
fi

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

# launch webpack ui dev server in background
#cd /seqr/ui
#npm run start &

# launch django dev server in background
cd /seqr

pip install --upgrade -r requirements.txt
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

# launch django dev server in background
cd /seqr_settings
gunicorn -w 4 -c gunicorn_config.py wsgi:application &

#python manage.py runserver 0.0.0.0:8000 &


# sleep indenfinitely to prevent container from terminating
sleep 1000000000000
