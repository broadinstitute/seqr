#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date


p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("--ped", help="ped file")
p.add_argument("--xls", help="xls file")
p.add_argument("-f", "--force", help="Force annotation", action="store_true")
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
opts = p.parse_args()

xls = opts.xls
ped = opts.ped
project_id = opts.project_id

if xls and not os.path.isfile(xls):
    p.error("xls file not found: " + xls)

if ped and not os.path.isfile(ped):
    p.error("ped file not found: " + ped)

if ped:
    os.system("cp %(ped)s %(project_id)s.ped" % locals())

commands = []
if xls:
    commands += [
        "python2.7 -u manage.py convert_xls_to_ped --xls '%(xls)s' --ped '%(project_id)s.ped' ",
    ]

commands += [
    "python2.7 -u manage.py add_individuals_to_project %(project_id)s --ped '%(project_id)s.ped' ",
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

