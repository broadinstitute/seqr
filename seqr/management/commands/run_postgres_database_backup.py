import os
from django.core.management.base import BaseCommand
import datetime


class Command(BaseCommand):
    help = 'Run database backups.'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', default=os.environ.get('DATABASE_BACKUP_BUCKET', 'unknown'))
        parser.add_argument('--postgres-host', default=os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'unknown'))
        parser.add_argument('--deployment-type', default=os.environ.get('DEPLOYMENT_TYPE', 'unknown'))

    def handle(self, *args, **options):

        def run(cmd):
            self.stdout.write(cmd)
            os.system(cmd)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")

        self.stdout.write("=====================================")
        self.stdout.write("======== %s ======= " % timestamp)
        self.stdout.write("=====================================")

        backup_dir = "/postgres_backups"
        if not os.path.isdir(backup_dir):
            self.stdout.write("Creating directory: " + backup_dir)
            os.mkdir(backup_dir)

        for db_name in ['seqrdb', 'xwiki']:
            backup_filename = "{db_name}_{deployment_type}_backup_{timestamp}.txt.gz".format(
                db_name=db_name, deployment_type=options['deployment_type'], timestamp=timestamp)

            run("/usr/bin/pg_dump -U postgres --host {postgres_host} {db_name} | gzip -c - > {backup_dir}/{backup_filename}".format(
               postgres_host=options['postgres_host'], db_name=db_name, backup_dir=backup_dir,
                backup_filename=backup_filename
            ))
            run("/usr/local/bin/gsutil mv {backup_dir}/{backup_filename} gs://{bucket}/postgres/{backup_filename}".format(
                backup_dir=backup_dir, backup_filename=backup_filename, bucket=options['bucket']
            ))
