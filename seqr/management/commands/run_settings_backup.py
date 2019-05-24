import os
import datetime
from django.core.management.base import BaseCommand


def run(cmd):
    print(cmd)
    os.system(cmd)


class Command(BaseCommand):
    help = 'Create a new user.'

    def add_arguments(self, parser):
        parser.add_argument('--deployment-type', default='unknown')

    def handle(self, *args, **options):
        os.chdir('/')

        filename = 'seqr_{deployment_type}_settings_{timestamp}.tar.gz'.format(
            deployment_type=args['deployment_type'], timestamp=datetime.datetime.now().strftime('%Y-%m-%d__%H-%M-%S'))

        run('tar czf {} /seqr_settings'.format(filename))
        run('gsutil mv {filename} gs://seqr-backups/settings_backups/'.format(filename=filename, bucket=args['bucket']))


