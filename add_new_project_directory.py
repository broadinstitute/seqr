#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date


p = argparse.ArgumentParser("")
p.add_argument("directories", help="The project directory", nargs=1)
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
p.add_argument("-f", dest="force", action="store_true", help="Force annotations")
p.add_argument("-i", dest="project_id", help="optional project id")
opts = p.parse_args()

project_dir = opts.directories[0]

project_id = opts.project_id
if not opts.project_id:
    project_yaml = yaml.load(open(os.path.join(project_dir, "project.yaml")))
    project_id = project_yaml['project_id']

commands = [
    # "kill `pgrep -f continuously_reload_all_projects_daemon.sh`",
    "python2.7 -u manage.py add_project %(project_id)s", 
    "python2.7 -u manage.py load_project_dir %(project_id)s %(project_dir)s", 
    "python2.7 -u manage.py load_project --force-annotations --force-clean %(project_id)s", 
    "python2.7 -u manage.py load_project_datastore %(project_id)s",
#    "nohup ./continuously_reload_all_projects_daemon.sh &> logs/continuously_load_all_projects_daemon.log &"
]
commands = map(lambda s: s % globals(), commands )

print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- Will run: "))
for c in commands:
    print(c)
#i = input("Do you want to continue? [y/n] ")
if opts.run:
    for c in commands:
        print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Running: " + c)
        print("Running " + str(c))
        r = os.system(c)
        if r != 0:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Command failed: " + c + "\nExiting.." )
            break

