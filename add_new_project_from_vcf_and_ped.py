#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date


p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("-v", "--vcf", help="The vcf file", required=True)
p.add_argument("-p", "--ped", help="The ped file", required=True)
p.add_argument("-f", "--force", help="Force annotation", action="store_true")
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
opts = p.parse_args()

vcf = opts.vcf
ped = opts.ped
project_id = opts.project_id

if not os.path.isfile(vcf):
    p.error("Invalid vcf: " + vcf)
if not os.path.isfile(ped):
    p.error("Invalid ped: " + ped)


commands = [
    "kill `pgrep -f continuously_reload_all_projects_daemon.sh`",
    "python2.7 -u manage.py add_project %(project_id)s", 
    "python2.7 -u manage.py add_individuals_to_project %(project_id)s --ped %(ped)s", 
    "python2.7 -u manage.py add_vcf_to_project %(project_id)s %(vcf)s", 
    "python2.7 -u manage.py load_project %(project_id)s" + (" --force-annotations --force-clean " if opts.force else ""), 
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
        r = os.system(c)
        if "continuously_reload_all_projects_daemon.sh" not in c and r != 0:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Command failed: " + c + "\nExiting.." )
            break

