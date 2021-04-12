import os
from django.core.management.base import BaseCommand
import datetime

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run database backups.'

    def add_arguments(self, parser):
        parser.add_argument('--postgres-host', default=os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'unknown'))
        parser.add_argument('--timestamp-name', action='store_true')

    def handle(self, *args, **options):

        def run(cmd):
            logger.info(cmd)
            os.system(cmd)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")

        logger.info("=====================================")
        logger.info("======== %s ======= " % timestamp)
        logger.info("=====================================")

        file_timestamp = '_{}'.format(timestamp) if options['timestamp_name'] else ''
        backup_filename = 'gene_reference_data_backup{}.gz'.format(file_timestamp)

        run("/usr/bin/pg_dump -U postgres --host {postgres_host} reference_data_db | gzip -c - > {backup_filename}".format(
            postgres_host=options['postgres_host'], backup_filename=backup_filename
        ))
        run("gsutil mv {backup_filename} gs://seqr-reference-data/{backup_filename}".format(backup_filename=backup_filename))
