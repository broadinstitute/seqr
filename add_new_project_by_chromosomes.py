#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date
import subprocess

p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("-p", "--ped", help="The ped file")
p.add_argument("-d", "--dont-add", help="Don't run the add_project command.", action="store_true")
p.add_argument("-j", "--json", help="JSON files to deserialize", action="append")
p.add_argument("-f", "--force", help="Force annotation", action="store_true")
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")

p.add_argument("vcfs", nargs="+", help="The vcf files")
opts = p.parse_args()

ped = opts.ped
project_id = opts.project_id

for vcf in opts.vcfs:
    if not os.path.isfile(vcf):
        p.error("Invalid vcf: " + vcf)
if ped and not os.path.isfile(ped):
    p.error("Invalid ped: " + ped)


commands = []
commands += [ "kill `pgrep -f continuously_reload_all_projects_daemon.sh`" ]
if not opts.dont_add:
    commands += [ "python2.7 -u manage.py add_project %(project_id)s" ]

if ped:  
    commands += [ "python2.7 -u manage.py add_individuals_to_project %(project_id)s --ped %(ped)s" ]

#  "python2.7 -u manage.py load_project_datastore %(project_id)s",
#  "nohup ./continuously_reload_all_projects_daemon.sh &> logs/continuously_load_all_projects_daemon.log &"

parallel_commands = ["python2.7 -u manage.py add_vcf_to_project --load %s %s > logs/%s_weisburd__load_%s.log" % (project_id, vcf, date.strftime(datetime.now(), "%Y_%m_%d"), os.path.basename(vcf))
                     for vcf in opts.vcfs]


commands = map(lambda s: s % globals(), commands)




print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- Will run: "))
for c in commands:
    print(c)
print("\nIn parallel:")
for p in parallel_commands:
    print(p)

#i = input("Do you want to continue? [y/n] ")
if opts.run:
    # add metadata
    for c in commands:
        print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Running: " + c)
        sys.stdout.flush()
        r = os.system(c)
        if "continuously_reload_all_projects_daemon.sh" not in c and r != 0:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + " -- Command failed: " + c + "\nExiting.." )
            break

    # load VCFs
    for c in parallel_commands:
        subprocess.call("nohup " + c + "&", shell=True)
