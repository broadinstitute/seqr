#!/usr/bin/env bash

set -x

env

source ~/.bashrc_custom

echo SHELL: $SHELL
echo PATH: $PATH
echo PYTHONPATH: $PYTHONPATH
echo
echo SPARK_HOME: $SPARK_HOME
echo SPARK_CLASSPATH: $SPARK_CLASSPATH
echo HAIL_HOME: HAIL_HOME


# init gcloud
#gcloud config set project $GCLOUD_PROJECT
#gcloud config set compute/zone $GCLOUD_ZONE

# launch django dev server in background
cd /seqr

pip install --upgrade -r requirements.txt
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check

# launch django dev server in background
cd /seqr_settings

#python manage.py runserver 0.0.0.0:8000 &

# launch jupyter notebook in background

mkdir /ipython_notebooks
cd /ipython_notebooks
nohup jupyter notebook --ip=0.0.0.0 --port=30005 --allow-root --NotebookApp.token='' &

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
