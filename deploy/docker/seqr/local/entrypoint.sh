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

# launch webpack ui dev server in background
cd /seqr/ui
npm run start &

# launch django dev server in background
cd /seqr
python manage.py runserver &

# sleep to keep image running even if servers are killed / restarted during development
sleep 1000000000000
