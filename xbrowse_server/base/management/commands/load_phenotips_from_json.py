from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
#from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project

import json
from pprint import pprint
import requests


def do_authenticated_call_to_phenotips(url, patient_data, username, passwd):

    return requests.put(url, data=json.dumps(patient_data), auth=(username, passwd))



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-t', '--test', help="only test parsing. Don't load yet", action="store_true")
        parser.add_argument('project_id')
        parser.add_argument('json_file')

    def handle(self, *args, **options):
        project_id = options['project_id']
        json_file = options['json_file']

        project = Project.objects.get(project_id=project_id)

        for patient_json in json.load(open(json_file)):
            indiv_id = patient_json['external_id']
            del patient_json["report_id"]

            indiv = Individual.objects.get(project=project, indiv_id=indiv_id)
            patient_json['external_id'] = indiv.phenotips_patient_id

            print("=====================================")
            print("Updating %s   https://seqr.broadinstitute.org/project/%s/family/%s" % (indiv.phenotips_id, project_id, indiv.family.family_id))
            pprint(patient_json)

            if options['test']:
                continue  # skip the actual commands

            #username, passwd = get_uname_pwd_for_project(project_id, read_only=False)
            response = do_authenticated_call_to_phenotips("http://localhost:9010/rest/patients/eid/"+patient_json['external_id'], patient_json,  "Admin", "admin")
            if response.status_code != 204:
                print("ERROR: " + str(response))


