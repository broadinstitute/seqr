import os
import datetime
from django.core.management.base import BaseCommand


def run(cmd):
    print(cmd)
    os.system(cmd)


class Command(BaseCommand):
    help = 'Run settings backups.'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', default=os.environ.get('DATABASE_BACKUP_BUCKET', 'unknown'))
        parser.add_argument('--deployment-type', default=os.environ.get('DEPLOYMENT_TYPE', 'unknown'))

    def handle(self, *args, **options):
        os.chdir('/')

        filename = 'seqr_{deployment_type}_settings_{timestamp}.tar.gz'.format(
            deployment_type=options['deployment_type'], timestamp=datetime.datetime.now().strftime('%Y-%m-%d__%H-%M-%S'))

        run('tar czf {} /seqr_settings'.format(filename))
        run('gsutil mv {filename} gs://{bucket}/settings/'.format(filename=filename, bucket=options['bucket']))


