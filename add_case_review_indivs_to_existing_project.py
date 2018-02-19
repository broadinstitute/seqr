#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date


p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("--xls", help="An xls file")
p.add_argument("--ped", help="A ped file")
p.add_argument("-f", "--force", help="Force annotation", action="store_true")
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
opts = p.parse_args()

project_id = opts.project_id
xls = opts.xls
ped = opts.ped

assert xls or ped

if xls and not os.path.isfile(xls):
    p.error("xls file not found: " + xls)

if ped and not os.path.isfile(ped):
    p.error("ped file not found: " + xls)

commands = []
if xls: 
    ped = project_id + ".ped"
    commands += ["python2.7 -u manage.py convert_xls_to_ped --xls '%(xls)s' --ped '%(ped)s' ",]
    
commands += [
    "python2.7 -u manage.py add_individuals_to_project %(project_id)s --ped '%(project_id)s.ped' --case-review ",
    "python2.7 -u manage.py generate_pedigree_images %(project_id)s",
    "python2.7 -u manage.py add_individuals_to_phenotips %(project_id)s --ped '%(project_id)s.ped' ",
]
commands = map(lambda s: s % globals(), commands )

print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- Will run: "))
for c in commands:
    print(c)

if opts.run:
    for c in commands:
        print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Running: " + c)
        sys.stdout.flush()
        r = os.system(c)
        if "continuously_reload_all_projects_daemon.sh" not in c and r != 0:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Command failed: " + c + "\nExiting.." )
            break

