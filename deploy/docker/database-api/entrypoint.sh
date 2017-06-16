#!/usr/bin/env bash

set -x

source /root/.bashrc
env

echo SHELL: $SHELL
echo HOME: $HOME

echo 'starting seqrserver.py...'
python seqrserver.py &

# sleep indefinitely to prevent container from terminating
sleep 1000000000000
