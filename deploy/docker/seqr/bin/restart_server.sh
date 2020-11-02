#!/usr/bin/env bash

# Pipe logs to the stdout for the main running kubernetes process (/proc/1/fd/1), instead of to the stdout of the bash
# process where this command is executed. This maintains the correct behavior for kubernetes log forwarding
stop_server.sh ; start_server.sh > /proc/1/fd/1
