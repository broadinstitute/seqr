from django.core.management.base import BaseCommand
from xbrowse_server import xbrowse_controls
from xbrowse_server.base.models import Cohort, Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        for project in Project.objects.all():
            if not project.is_loaded():
                xbrowse_controls.reload_project(project.project_id)
        #
        # # reload any cohorts that were recently created
        # for cohort in Cohort.objects.all():
        #     if cohort.get_data_status() == 'no_variants' and not cohort.project.needs_reload():
        #         xbrowse_controls.reload_cohort_variants(cohort.project.project_id, cohort.cohort_id)