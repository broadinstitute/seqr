from collections import defaultdict
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import User, Project, Family, AnalysisStatus

class Command(BaseCommand):
    """Command to copy Family.analysis_status into the new AnalysisStatus table. Family.analysis_status will later be deleted. """

    def handle(self, *args, **options):
        counter = defaultdict(int)
        for family in Family.objects.all():
            counter['total'] += 1
            if family.analysis_status:
                analysis_status, created = AnalysisStatus.objects.get_or_create(family=family)
                analysis_status.status=family.analysis_status
                analysis_status.save()
                counter['modified'] += 1

        print("%s of %s (%s%%) families migrated" % (counter['modified'], counter['total'], 100.0*counter['modified']/float(counter['total'])))
