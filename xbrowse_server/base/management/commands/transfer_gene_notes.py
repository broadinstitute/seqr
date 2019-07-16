import logging
from tqdm import tqdm

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import GeneNote as BaseGeneNote
from seqr.models import GeneNote as SeqrGeneNote

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer gene lists to the new seqr schema'

    def add_arguments(self, parser):
        #parser.add_argument('-u', '--username', help="Username of project owner", required=True)
        pass

    def handle(self, *args, **options):
        """For each xbrowse_server.base.models.GeneNote, create a corresponding seqr.models.GeneNote
        """
        created_count = 0
        for note in tqdm(BaseGeneNote.objects.all(), unit=" gene notes"):
            new_note, created = SeqrGeneNote.objects.get_or_create(
                created_by=note.user,
                created_date=note.date_saved,
                note=note.note,
                gene_id=note.gene_id,
            )
            new_note.save(last_modified_date=note.date_saved)

            if created:
                created_count += 1

        logger.info("Done")
        logger.info("Created %s gene notes" % (created_count))
