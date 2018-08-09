from __future__ import print_function

import json
import requests
from pprint import pformat

from django.core.management.base import BaseCommand, CommandError
from xbrowse_server.base.models import Project, Individual
from settings import PHENOTIPS_SERVICE_HOSTNAME, PHENOTIPS_PORT
from django.core.exceptions import ObjectDoesNotExist

def phenotips_GET(url, username, passwd):
    """
        Does a GET into PhenoTips
        Args:
            url: the URL to post to
            username: the username to authenticate against PhenoTips
            passwd: the password to use
        Returns:
            A requests.get response
    """
    return requests.get(url, auth=(username, passwd))


def phenotips_PUT(url, patient_data, username, passwd):
    """
        Does a PUT into PhenoTips
        Args:
            url: the URL to post to
            patient_data: the patient data to put into PhenoTips
            username: the username to authenticate against PhenoTips
            passwd: the password to use
        Returns:
            A requests.put response
    """
    return requests.put(url, data=json.dumps(patient_data), auth=(username, passwd))


class Command(BaseCommand):
    """
        Command class interface into Django commands
    """
    def add_arguments(self, parser):
        parser.add_argument('-t', '--test', help="Used to test parsing. Does actually change anything in seqr.", action="store_true")
        parser.add_argument('--patient-id-mapping', nargs="?", help="text file that contains 2 columns: the 'Patient ID' value that's in the phenotips json and the corresponding seqr `Individual id`.")
        parser.add_argument('project_id', help="seqr project id")
        parser.add_argument('file_name', nargs="+", help="one or more file paths for json files that were exported from Phenotips using the 'Export Json' UI")

    def handle(self, *args, **options):
        project_id = options['project_id']
        file_names = options['file_name']
        patient_id_mapping = options.get('patient_id_mapping')
        
        if patient_id_mapping:
            with open(patient_id_mapping) as patient_id_to_indiv_id_mapping:
                rows = patient_id_to_indiv_id_mapping.read().strip().split("\n")

                patient_id_to_indiv_id_mapping = {}
                for i, row in enumerate(rows):
                    fields = row.strip().split()
                    if len(fields) != 2:
                        raise CommandError((
                           "%s row %s contains %s columns. Expected 2 columns. "
                           "Column 1 = the phenotips patient id and "
                           "Column 2 = the seqr individual id") % (
                            patient_id_mapping, i, len(fields)))
                    patient_id_to_indiv_id_mapping[fields[0]] = fields[1]
        else:
            patient_id_to_indiv_id_mapping = {}

        for file_name in file_names:
            self.process_json_file(file_name, patient_id_to_indiv_id_mapping, project_id, is_test_only=options['test'])
                
                
                
    def process_json_file(self, file_name, patient_id_to_indiv_id_mapping, project_id, is_test_only=False):
        """
        Process a JSON file that was exported from a PhenoTips instance
        Args:
            file_name (string): A file (json) that had been exported from PhenoTips
            patient_id_to_indiv_id_mapping (dict): a mapping file that specifies the link between a seqr ID and external ID
            project_id (string): the project that this individual belongs to
            is_test_only (bool): if True, phenotips records won't be modified.
        """
        print("Processing {}".format(file_name))
        with open(file_name) as json_file:
            patient_json = json.load(json_file)

            #sometimes a JSON list is given; that contains a list of patients, vs a single patient
            if type(patient_json) is list:
                for patient in patient_json:
                    self.process_single_patient_json_file(patient, patient_id_to_indiv_id_mapping, project_id, is_test_only=is_test_only)
            else:
                self.process_single_patient_json_file(patient_json, patient_id_to_indiv_id_mapping, project_id, is_test_only=is_test_only)

    def process_single_patient_json_file(self, patient_json, patient_id_to_indiv_id_mapping, project_id, is_test_only=False):
        """
        Process a single patient JSON file that was exported from a PhenoTips instance
        Args:
            patient_json (dict): A JSON format file that had been downloaded from PhenoTips of a single patient
            patient_id_to_indiv_id_mapping (dict): a mapping file that specifies the link between a seqr ID and external ID
            project_id (string): the project that this individual belongs to
            is_test_only (bool): if True, phenotips records won't be modified. 
        """  
        print("Loading " + pformat(patient_json))
        if 'report_id' in patient_json and patient_json['report_id'] in patient_id_to_indiv_id_mapping:
            indiv_id = patient_id_to_indiv_id_mapping[patient_json['report_id']]
            del patient_json["report_id"]
        else:
            indiv_id = patient_json['external_id']

        indiv_id = indiv_id.split(' ')[0]
        try:
            project = Project.objects.get(project_id=project_id)
            indiv = Individual.objects.get(project=project, indiv_id=indiv_id)
        except ObjectDoesNotExist as e:
            print("Warning: %(indiv_id)s not found in seqr project %(project)s. Skipping.." % locals())
            return
            
        patient_json['external_id'] = indiv.phenotips_id

        print("Patient external id: " + patient_json['external_id'])
        print("=====================================")

        response = phenotips_GET("http://"+PHENOTIPS_SERVICE_HOSTNAME+":"+str(PHENOTIPS_PORT)+"/rest/patients/eid/"+patient_json['external_id'], "Admin", "admin")
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
                if (existing_patient_in_phenotips[k] and type(existing_patient_in_phenotips[k]) != type({})) or (type(existing_patient_in_phenotips[k]) == type({}) and [v for v in existing_patient_in_phenotips[k].values() if v]):
                    if (patient_json[k] and type(patient_json[k]) != type({})) or (type(patient_json[k]) == type({}) and [v for v in patient_json[k].values() if v]):
                        print("%s:\n  our data: %s\n  their data:%s" % (k, existing_patient_in_phenotips[k], patient_json[k]))
                else:
                    pass

        # skip the rest if test only
        if is_test_only:
            return

        username, passwd = ("Admin", "admin")   # get_uname_pwd_for_project(project_id, read_only=False)
        response = phenotips_PUT("http://"+PHENOTIPS_SERVICE_HOSTNAME+":"+str(PHENOTIPS_PORT)+"/rest/patients/eid/"+patient_json['external_id'], patient_json, username, passwd)

        if response.status_code != 204:
            print("ERROR: %s %s" % (response.status_code, response.reason))
        else:
            indiv.phenotips_data = json.dumps(patient_json)
            indiv.save()
    
