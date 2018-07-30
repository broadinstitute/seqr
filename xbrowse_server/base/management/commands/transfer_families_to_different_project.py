from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily
from xbrowse_server.base.model_utils import update_xbrowse_model
from seqr.views.apis.phenotips_api import _get_phenotips_uname_and_pwd_for_project, _add_user_to_patient, \
    sync_phenotips_data, phenotips_patient_exists


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)
        parser.add_argument('family_ids', nargs='+')

    def handle(self, *args, **options):
        from_project = BaseProject.objects.get(project_id=options['from_project'])
        to_project = BaseProject.objects.get(project_id=options['to_project'])
        family_ids = options['family_ids']
        families = BaseFamily.objects.filter(project=from_project, family_id__in=family_ids)
        print('Found {} out of {} families. No match for: {}.'.format(len(families), len(set(family_ids)), set(family_ids) - set([f.family_id for f in families])))

        for f in families:
            print("==> Moving {}".format(f))
            for individual in f.individual_set.all():
                if phenotips_patient_exists(to_project.seqr_project, individual.seqr_individual):
                    sync_phenotips_data(to_project.seqr_project, individual.seqr_individual)

                    phenotips_readonly_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.seqr_project.phenotips_user_id, read_only=True)
                    _add_user_to_patient(phenotips_readonly_username, individual.seqr_individual.phenotips_patient_id, allow_edit=False)

                    phenotips_readwrite_username, _ = _get_phenotips_uname_and_pwd_for_project(to_project.seqr_project.phenotips_user_id, read_only=False)
                    _add_user_to_patient(phenotips_readwrite_username, individual.seqr_individual.phenotips_patient_id, allow_edit=True)
            update_xbrowse_model(f, project=to_project)

        print("Done.")
