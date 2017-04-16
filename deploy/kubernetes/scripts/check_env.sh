#!/usr/bin/env bash

if [ -z "$STARTED_VIA_SEQRCTL" ]; then
    echo 'Environment variables not set. Please use seqrctl script to run these commands.'
    exit 1
fi
