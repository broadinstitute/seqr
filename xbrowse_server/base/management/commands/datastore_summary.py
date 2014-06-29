from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
    )

    def handle(self, *args, **options):

        # default display is individuals
        if len(args) > 0:
            display = args[0]
        else:
            display = 'individuals'

        if display == 'families':
            for project_id, family_id in settings.DATASTORE.get_all_families():
                fields = [
                    project_id,
                    family_id,
                    ",".join(settings.DATASTORE.get_individuals_for_family(project_id, family_id))
                ]
                print "\t".join(fields)

        elif display == 'individuals':
            for project_id, indiv_id in settings.DATASTORE.get_all_individuals():
                print "\t".join([project_id, indiv_id])