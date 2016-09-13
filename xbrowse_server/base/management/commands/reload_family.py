from django.core.management.base import BaseCommand
from xbrowse_server import xbrowse_controls

from xbrowse_server.base.models import Project
from xbrowse_server.mall import get_datastore


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('project_id')
        parser.add_argument('family_ids', nargs='+')


    def handle(self, *args, **options):

        project_id = options["project_id"]
        family_ids = options["family_ids"]
        project = Project.objects.get(project_id=project_id)

        already_deleted_once = set()  # set of family ids for which get_datastore(project_id).delete_family has already been called once
        for vcf_file, families in project.families_by_vcf().items():
            families_to_load = []
            for family in families:
                family_id = family.family_id
                print("Checking id: " + family_id)
                if not family_ids or family.family_id not in family_ids:
                    continue

                # delete this family
                if family_id not in already_deleted_once:
                    get_datastore(project_id).delete_family(project_id, family_id)
                    already_deleted_once.add(family_id)

                families_to_load.append(family)

            # reload family
            print("Loading %(project_id)s %(families_to_load)s" % locals())
            xbrowse_controls.load_variants_for_family_list(project, families_to_load, vcf_file)




