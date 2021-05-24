import csv
from django.core.management.base import BaseCommand
import logging
import tqdm

from seqr.models import Project

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Get all collaborators for seqr projects'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*', help='only get collaborators for these project name(s)')

    def handle(self, *args, **options):
        projects = Project.objects.filter(name__in=args ) if args else Project.objects.all()
        projects = projects.prefetch_related('can_view_group__user_set', 'can_edit_group__user_set')

        rows = []
        for project in tqdm.tqdm(projects, unit=" samples"):
            managers = {u.email for u in project.can_edit_group.user_set.all()}
            collaborators = {u.email for u in project.can_view_group.user_set.all() if u.email not in managers}
            rows.append({
                'project': project.name,
                'managers': ', '.join(managers),
                'collaborators': ', '.join(collaborators),
            })

        with open('project_collaborators.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['project', 'managers', 'collaborators'])
            writer.writeheader()
            writer.writerows(rows)
