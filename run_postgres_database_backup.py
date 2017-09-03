#!/usr/bin/env python2.7

import os
import datetime
timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")

backup_dir = "/postgres_backups"
if not os.path.isdir(backup_dir):
   print("Creating directory: " + backup_dir)
   os.mkdir(backup_dir)

for db_name in ['seqrdb', 'xwiki']:
   backup_filename = "%(db_name)s_backup_%(timestamp)s.txt.gz" % locals()
   cmd = "pg_dump -U postgres  %(db_name)s | gzip -c - > %(backup_dir)s/%(backup_filename)s" % locals()
   print(cmd)
   os.system(cmd)

   cmd = "gsutil -m cp %(backup_dir)s/%(backup_filename)s gs://seqr-database-backups/%(backup_filename)s" % locals()
   print(cmd)
   os.system(cmd)
