from optparse import make_option
import settings
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Checks for variants that are in the VCF but not in the mongodb annotator datastore which could indicate a bug
    during loading (unless xBrowse ran VEP with the --filter flag)"""

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-n', dest='number_of_variants_to_check')

    def handle(self, *args, **options):
        #['project_id', 'family_id', 'search_mode', 'variant_filter',
        # 'quality_filter', 'inheritance_mode', 'burden_filter', 'genotype_filter', 'search_hash']

        if not args:
            args = [p.project_id for p in Project.objects.all()]

        for project_id in args:
            print("------------")
            for i, log_data in enumerate( settings.LOGGING_DB.pageviews.find({"project_id": project_id}).sort([('date', -1)])):
                if i > 10:
                    break
                print("%(date)s %(username)s - project: %(project_id)s - page: %(page)s " % log_data)

            print("Done")
