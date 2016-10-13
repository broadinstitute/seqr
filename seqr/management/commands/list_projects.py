from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import models
from xbrowse2.models import Project


class Command(BaseCommand):
    help = 'Print a list of projects. If no options are specified, all projects will be printed.'

    def add_arguments(self, parser):
        parser.add_argument('project-id', nargs='*')

    def handle(self, *args, **options):
        if not args:
            projects = Project.objects.all()
        else:
            projects = []
            for project_id in args:
                try:
                    project = Project.objects.get(id=project_id)
                except models.Model.DoesNotExist:
                    print("Project id not found: " + project_id)
                else:
                    projects.append(project)

        print("-- %d project(s) --" % len(projects))
        for project in projects:
            self.print_project(project)


    def print_project(self, project):
        """Utility method that prints out a single project."""
        print("  %15s   %40s      %s      %s" % (project.id, project.name, project.created_by, project.created_date))
