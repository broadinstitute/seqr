import os
from django.core.management.base import BaseCommand
import datetime


class Command(BaseCommand):
    help = 'Run database backups.'

    def add_arguments(self, parser):
        parser.add_argument('--postgres-host', default=os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'unknown'))

    def handle(self, *args, **options):

        def run(cmd):
            self.stdout.write(cmd)
            os.system(cmd)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")

        self.stdout.write("=====================================")
        self.stdout.write("======== %s ======= " % timestamp)
        self.stdout.write("=====================================")

        backup_filename = 'gene_reference_data_backup.gz'

        run("/usr/bin/pg_dump -U postgres --host {postgres_host} reference_data_db | gzip -c - > {backup_filename}".format(
            postgres_host=options['postgres_host'], backup_filename=backup_filename
        ))
        run("gsutil mv {backup_filename} gs://seqr-reference-data/{backup_filename}".format(backup_filename=backup_filename))
