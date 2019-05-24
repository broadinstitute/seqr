import os
from django.core.management.base import BaseCommand
import datetime


def run(cmd):
    print(cmd)
    os.system(cmd)


class Command(BaseCommand):
    help = 'Run database backups.'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', required=True)
        parser.add_argument('--deployment-type', default='unknown')

    def handle(self, *args, **options):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")

        print("=====================================")
        print("======== %s ======= " % timestamp)
        print("=====================================")

        backup_dir = "/postgres_backups"
        if not os.path.isdir(backup_dir):
            print("Creating directory: " + backup_dir)
            os.mkdir(backup_dir)

        for db_name in ['seqrdb', 'xwiki']:
            backup_filename = "{db_name}_{deployment_type}_backup_{timestamp}.txt.gz".format(
                db_name=db_name, deployment_type=options['deployment_type'], timestamp=timestamp)
            exclude_table_arg = "--exclude-table='reference_*'" if db_name == "seqrdb" else ""

            run("/usr/bin/pg_dump -U postgres {exclude_table_arg} {db_name} | gzip -c - > {backup_dir}/{backup_filename}".format(
                exclude_table_arg=exclude_table_arg, db_name=db_name, backup_dir=backup_dir, backup_filename=backup_filename
            ))
            run("gsutil mv {backup_dir}/{backup_filename} gs://{bucket}/postgres/{backup_filename}".format(
                backup_dir=backup_dir, backup_filename=backup_filename, bucket=options['bucket']
            ))
