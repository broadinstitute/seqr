#!/usr/bin/env python2.7
import sys
import os
import argparse
import yaml
from datetime import datetime, date


p = argparse.ArgumentParser("")
p.add_argument("-i", "--project-id", help="Project id", required=True)
p.add_argument("-n", "--project-name", help="Project name", required=True)
p.add_argument("--xls", help="The xls file", required=True)
p.add_argument("-f", "--force", help="Force annotation", action="store_true")
p.add_argument("--case-review", action="store_true", help="Whether these are case review samples")
p.add_argument("-r", dest="run", action="store_true", help="Actually run the commands")
opts = p.parse_args()

xls = opts.xls
project_id = opts.project_id
project_name = opts.project_name
case_review = "--case-review" if opts.case_review else ""
if xls and not os.path.isfile(xls):
    p.error("xls file not found: " + xls)

commands = [
    "python2.7 -u manage.py add_project %(project_id)s '%(project_name)s' ",
    "python2.7 -u manage.py convert_xls_to_ped --xls '%(xls)s' --ped %(project_id)s.ped ",
    "python2.7 -u manage.py add_individuals_to_project  %(project_id)s %(case_review)s --ped %(project_id)s.ped ",
    "python2.7 -u manage.py generate_pedigree_images %(project_id)s",
    "python2.7 -u manage.py add_default_tags %(project_id)s",
    "python2.7 -u manage.py add_project_to_phenotips %(project_id)s '%(project_name)s' ",
    "python2.7 -u manage.py add_individuals_to_phenotips %(project_id)s --ped %(project_id)s.ped ",
    "python2.7 -u manage.py add_custom_population_to_project %(project_id)s gnomad-exomes", 
    "python2.7 -u manage.py add_custom_population_to_project %(project_id)s gnomad-genomes",
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

    print("Done with https://seqr.broadinstitute.org/project/%(project_id)s" % locals())
