import collections
import logging
from tqdm import tqdm

from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm

from xbrowse_server.gene_lists.models import GeneList
from seqr.models import IS_OWNER, CAN_EDIT, CAN_VIEW, LocusList, LocusListEntry
from reference_data.models import GENOME_BUILD_GRCh37

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer gene lists to the new seqr schema'

    def add_arguments(self, parser):
        #parser.add_argument('-u', '--username', help="Username of project owner", required=True)
        pass

    def handle(self, *args, **options):
        """For each xbrowse_server.gene_lists.models.GeneList, create a corresponding
        seqr.models.LocusList

        GeneList fields:
        slug = models.SlugField(max_length=40)
        name = models.CharField(max_length=140)
        description = models.TextField()
        is_public = models.BooleanField(default=False)
        owner = models.ForeignKey(User, null=True, blank=True)
        last_updated = models.DateTimeField(null=True, blank=True)

        GeneListItem fields:
        gene_id = models.CharField(max_length=20)  # ensembl ID
        gene_list = models.ForeignKey(GeneList)
        description = models.TextField(default="")
        """
        counters = collections.defaultdict(int)
        for source_list in tqdm(GeneList.objects.all(), unit=" gene lists"):
            counters['gene lists processed'] += 1
            # create LocusList
            destination_list, created = LocusList.objects.get_or_create(
                created_by=source_list.owner,
                name=source_list.name or source_list.slug,
                is_public=source_list.is_public
            )
            destination_list.description=source_list.description
            destination_list.last_modified_date = source_list.last_updated
            destination_list.last_modified_by = source_list.owner
            destination_list.save()

            if created:
                counters['LocusLists created'] += 1

            # create LocusListEntry for each gene
            for source_item in source_list.genelistitem_set.all():
                counters['genes processed'] += 1

                destination_item, created = LocusListEntry.objects.get_or_create(
                    created_by=source_list.owner,
                    parent=destination_list,
                    genome_build_id=GENOME_BUILD_GRCh37,
                    feature_id=source_item.gene_id.upper(),
                    comment=source_item.description,
                )
                if created:
                    counters['LocusListEntry\'s created'] += 1

            # set LocusList permissions
            if source_list.owner is not None:
                assign_perm(user_or_group=source_list.owner, perm=IS_OWNER, obj=destination_list)
                assign_perm(user_or_group=source_list.owner, perm=CAN_EDIT, obj=destination_list)
                assign_perm(user_or_group=source_list.owner, perm=CAN_VIEW, obj=destination_list)

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            logger.info("  %s: %s" % (k, v))
