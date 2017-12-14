from __future__ import print_function

import json
import requests
from pprint import pformat

from django.core.management.base import BaseCommand, CommandError
from xbrowse_server.base.models import Project, Individual
from settings import PHENOTIPS_SERVICE_HOSTNAME, PHENOTIPS_PORT
from django.core.exceptions import ObjectDoesNotExist


def phenotips_GET(url, username, passwd):

    return requests.get(url, auth=(username, passwd))

def phenotips_PUT(url, patient_data, username, passwd):

    return requests.put(url, data=json.dumps(patient_data), auth=(username, passwd))


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-t', '--test', help="Used to test parsing. Does actually change anything in seqr.", action="store_true")
        parser.add_argument('project_id', help="seqr project id")
        parser.add_argument('json_file', help=".json file that was exported from Phenotips using the 'Export' UI")
        parser.add_argument('patient_id_to_indiv_id_mapping', nargs="?", help="text file that maps the 'Patient ID' value that's in the phenotips json to the corresponding seqr individual id.")

    def handle(self, *args, **options):
        project_id = options['project_id']
        json_file = options['json_file']
        patient_id_to_indiv_id_mapping_file_path = options.get('patient_id_to_indiv_id_mapping')
        
        if patient_id_to_indiv_id_mapping_file_path:
            with open(patient_id_to_indiv_id_mapping_file_path) as patient_id_to_indiv_id_mapping:
                rows = patient_id_to_indiv_id_mapping.read().strip().split("\n")

                patient_id_to_indiv_id_mapping = {}
                for i, row in enumerate(rows):
                    fields = row.strip().split()
                    if len(fields) != 2:
                        raise CommandError((
                           "%s row %s contains %s columns. Expected 2 columns. "
                           "Column 1 = the phenotips patient id and "
                           "Column 2 = the seqr individual id") % (
                                patient_id_to_indiv_id_mapping_file_path, i, len(fields)))
                    patient_id_to_indiv_id_mapping[fields[0]] = fields[1]
        else:
            patient_id_to_indiv_id_mapping = {}
            
        project = Project.objects.get(project_id=project_id)

        for patient_json in json.load(open(json_file)):
            print("Loading " + pformat(patient_json))
            if 'report_id' in patient_json and patient_json['report_id'] in patient_id_to_indiv_id_mapping:
                indiv_id = patient_id_to_indiv_id_mapping[patient_json['report_id']]
                del patient_json["report_id"]
            else:
                indiv_id = patient_json['external_id']

            indiv_id = indiv_id.split(' ')[0]
            try:
                indiv = Individual.objects.get(project=project, indiv_id=indiv_id)
            except ObjectDoesNotExist as e:
                print("Warning: %(indiv_id)s not found in seqr project %(project)s. Skipping.." % locals())
                continue
                
            patient_json['external_id'] = indiv.phenotips_id
            
            #with open(os.path.join(os.path.dirname(json_file), indiv.indiv_id + ".json"), 'w') as f:
            #    f.write(indiv.phenotips_data)
            #f.close()

            print("Patient external id: " + patient_json['external_id'])
            print("=====================================")
            #print("Updating %s   https://seqr.broadinstitute.org/project/%s/family/%s" % (indiv.phenotips_id, project_id, indiv.family.family_id))
            #if patient_json.get('features'): # and not indiv.phenotips_data['features']:
            #    pprint(indiv.phenotips_data) # patient_json)

            response = phenotips_GET("http://"+PHENOTIPS_SERVICE_HOSTNAME+":"+PHENOTIPS_PORT+"/rest/patients/eid/"+patient_json['external_id'], "Admin", "admin")
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

            # skip the rest if test only
            if options['test']:
                continue

            username, passwd = ("Admin", "admin")   # get_uname_pwd_for_project(project_id, read_only=False)
            response = phenotips_PUT("http://"+PHENOTIPS_SERVICE_HOSTNAME+":"+PHENOTIPS_PORT+"/rest/patients/eid/"+patient_json['external_id'], patient_json, username, passwd)

            if response.status_code != 204:
                print("ERROR: %s %s" % (response.status_code, response.reason))
            else:
                indiv.phenotips_data = json.dumps(patient_json)
                indiv.save()
