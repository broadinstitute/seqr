from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
import os
import json
from pprint import pprint
import requests
from pprint import pprint


def phenotips_GET(url, username, passwd):

    return requests.get(url, auth=(username, passwd))

def phenotips_PUT(url, patient_data, username, passwd):

    return requests.put(url, data=json.dumps(patient_data), auth=(username, passwd))



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-f', '--from', help="from project id")
        parser.add_argument('-d', '--destination', help="destination project id")
        parser.add_argument('-t', '--test', help="only test parsing. Don't load yet", action="store_true")

    def handle(self, *args, **options):
        from_id = options['from']
        destination_id = options['destination']
        print(from_id, destination_id)
        
        #json_file = options['json_file']

        from_project = Project.objects.get(project_id=from_id)
        destination_project = Project.objects.get(project_id=destination_id)

        for from_indiv in Individual.objects.filter(project=from_project):
            destination_indiv = Individual.objects.filter(project=destination_project, indiv_id=from_indiv.indiv_id)
            if destination_indiv:
                assert len(destination_indiv) == 1
                destination_indiv = destination_indiv[0]
                print("Found %s for %s" % (destination_indiv, from_indiv))
            else:
                print("Indiv not found for %s" % from_indiv)
                continue


            response = phenotips_GET("http://phenotips:8080/rest/patients/eid/"+from_indiv.phenotips_id, "Admin", "admin")
            phenotips_data = json.loads(response.content)
            #print(from_indiv)
            #pprint(phenotips_data)

            #destination_indiv.phenotips_data = json.dumps(phenotips_data)
            #print(destination_indiv.indiv_id + " replacing " + destination_indiv.phenotips_id + " with " + from_indiv.phenotips_id)
            #destination_indiv.phenotips_id = from_indiv.phenotips_id
            #destination_indiv.save()

            #print('============================')
            # transfer phenotips data to the new patient
            response = phenotips_GET("http://localhost:9010/rest/patients/eid/"+destination_indiv.phenotips_id, "Admin", "admin")
            destination_phenotips_data = json.loads(response.content)
            pprint(destination_phenotips_data)

            del phenotips_data['id']
            del phenotips_data['report_id']
            del phenotips_data['reporter']
            del phenotips_data['external_id']

            if options["test"]:
                continue

            print("Updating %s (%s)" % (destination_phenotips_data['id'], destination_phenotips_data['external_id']))
            response = phenotips_PUT("http://localhost:9010/rest/patients/"+destination_phenotips_data['id'], phenotips_data,  "Admin", "admin")
            if response.status_code != 204:
                print("ERROR: " + str(response))

            print('============================')
            print('============================')

