#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date

p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
opts = p.parse_args()

project_id = opts.project_id

commands = [
    "python2.7 -u manage.py delete_phenotips_patients %(project_id)s ",
    "python2.7 -u manage.py delete_project %(project_id)s ",
]

commands = map(lambda s: s % globals(), commands)

print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- Will run: "))
for c in commands:
    print(c)

if opts.run:
    response = raw_input("Are you sure you want to delete '%s'? [Y/n] " % project_id)
    if response.lower() != 'y':
        print("Canceling")
        sys.exit(0)

    for c in commands:
        print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Running: " + c)
        sys.stdout.flush()
        r = os.system(c)
        if "continuously_reload_all_projects_daemon.sh" not in c and r != 0:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Command failed: " + c + "\nExiting.." )
            break

