#!/usr/bin/env bash

# The semantic-ui install package install runs gulp and includes interactive prompts
#
# echo characters to work around the interactive steps
# (based on: https://github.com/Semantic-Org/Semantic-UI/issues/1816)

set -x

echo -ne '\n \n \3033[1B\nsemantic/\n\n' | npm install
