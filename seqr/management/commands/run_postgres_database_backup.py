import os
from django.core.management.base import BaseCommand
import datetime


class Command(BaseCommand):
    help = """Generate postgres database backups for the seqr (seqrdb) and phenotips (xwiki) databases. 
    Requires the postgres pg_dump utility to be installed and on PATH. 
    gsutil is required if backup files are to be copied to a google bucket.
    
    Later, to restore the seqr and phenotips databases from these backups, run 

    ./deploy/docker/postgres/restore_database_backup.sh postgres seqrdb $SEQRDB_BACKUP_FILE_PATH   # restores seqr metadata
    ./deploy/docker/postgres/restore_database_backup.sh postgres xwiki $XWIKI_BACKUP_FILE_PATH     # restore phenotips data
    """

    def add_arguments(self, parser):
        parser.add_argument('--bucket', help="(optional) if specified, backup files will be copied to this google bucket", default=os.environ.get('DATABASE_BACKUP_BUCKET'))
        parser.add_argument('--postgres-host', default=os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'localhost'))
        parser.add_argument('--deployment-type', help="(optional) a label to add to the backup filename", default=os.environ.get('DEPLOYMENT_TYPE', 'local'))

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

            run("pg_dump -U postgres --host {postgres_host} {db_name} | gzip -c - > {backup_dir}/{backup_filename}".format(
               postgres_host=options['postgres_host'], db_name=db_name, backup_dir=backup_dir,
                backup_filename=backup_filename
            ))
            
            if options.get('bucket'):
                run("gsutil -m cp {backup_dir}/{backup_filename} gs://{bucket}/postgres/{backup_filename}".format(
                    backup_dir=backup_dir, backup_filename=backup_filename, bucket=options['bucket']
                ))
