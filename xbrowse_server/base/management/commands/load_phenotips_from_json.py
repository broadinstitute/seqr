from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
#from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
import os
import json
from pprint import pprint
import requests


def phenotips_GET(url, username, passwd):

    return requests.get(url, auth=(username, passwd))

def phenotips_PUT(url, patient_data, username, passwd):

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

            
            indiv_id = "_".join(indiv_id.split('_')[-3:]).upper()
            print(indiv_id)
            indivs = Individual.objects.filter(project=project, indiv_id=indiv_id)
            if not indivs:
                print("Skipping...")
                continue
            indiv=indivs[0]
            
            patient_json['external_id'] = indiv.phenotips_id
            print(indiv_id)

                
            #with open(os.path.join(os.path.dirname(json_file), indiv.indiv_id + ".json"), 'w') as f:
            #    f.write(indiv.phenotips_data)
            #f.close()
            print("=====================================")
            #print("Updating %s   https://seqr.broadinstitute.org/project/%s/family/%s" % (indiv.phenotips_id, project_id, indiv.family.family_id))
            #if patient_json.get('features'): # and not indiv.phenotips_data['features']:
            #    pprint(indiv.phenotips_data) # patient_json)

            phenotips_host = os.environ.get("PHENOTIPS_SERVICE_HOST", "localhost")
            phenotips_port = os.environ.get("PHENOTIPS_SERVICE_PORT", "8080")

            response = phenotips_GET(("http://%(phenotips_host)s:%(phenotips_port)s/rest/patients/eid/" % locals())+patient_json['external_id'], "Admin", "admin")
            existing_patient_in_phenotips = json.loads(response.content)

            print("Sample: " + indiv_id)
            for k in patient_json:
                if k in ('last_modification_date', 'date', 'last_modified_by'):
                    continue
                if k == 'family_history' and not patient_json[k].get('consanguinity') and not patient_json[k].get('miscarriages'):
                    continue
                if k not in existing_patient_in_phenotips:
                    print("%s: %s" % (k, patient_json[k]))
                elif k == "features" and existing_patient_in_phenotips[k] != patient_json[k]:
                    for key in [patient_json[k] for k in (set(patient_json.keys()) - set(existing_patient_in_phenotips.keys()))]:
                        if key:
                            print("feature: " + str(key))
                elif existing_patient_in_phenotips[k] != patient_json[k]:
                    #print("%s : %s %s" % (k, len(patient_json[k]), type(patient_json[k])))
                    if (existing_patient_in_phenotips[k] and type(existing_patient_in_phenotips[k]) != type({})) or (type(existing_patient_in_phenotips[k]) == type({}) and [v for v in existing_patient_in_phenotips[k].values() if v]):
                        if (patient_json[k] and type(patient_json[k]) != type({})) or (type(patient_json[k]) == type({}) and [v for v in patient_json[k].values() if v]):
                            print("%s:\n  our data: %s\n  their data:%s" % (k, existing_patient_in_phenotips[k], patient_json[k]))
                    else:
                        pass
                        #if patient_json[k]:
                        #    print("%s: %s" % (k, patient_json[k]))
            if options['test']:
                continue  # skip the actual commands
            
 

            #username, passwd = get_uname_pwd_for_proPHENOTIPS_SERVICE_POject(project_id, read_only=False)
            response = phenotips_PUT(("http://%(phenotips_host)s:%(phenotips_port)s/rest/patients/eid/" % locals())+patient_json['external_id'], patient_json,  "Admin", "admin")

            if response.status_code != 204:
                print("ERROR: " + str(response))
            else:
                indiv.phenotips_data = json.dumps(patient_json)
                indiv.save()
