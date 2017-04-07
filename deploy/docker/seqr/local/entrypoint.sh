#!/usr/bin/env bash

set -x

env

while [ ! -f /seqr/manage.py ];
do
    echo "Waiting for /seqr directory to be mounted...";

    sleep 5;
done

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

ls -la1 /seqr/

# run these in the background
cd /seqr/ui
npm run start &

cd /seqr
python manage.py runserver &

# sleep indefinitely
sleep 1000000000000
