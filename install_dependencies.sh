#!/usr/bin/env bash

set -x
pip install -r requirements.txt --upgrade
pip install -r requirements-dev.txt --upgrade
cd ui/
echo -ne "\n \n \3033[1B\nsemantic/\n" | npm install
cd ..
