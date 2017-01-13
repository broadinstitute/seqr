import os
import requests
import settings
from slugify import slugify
import sys


from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--slugify', action="store_true", help="slugify the sample id")
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        """Command line args:
            arg0 = project id
            arg1 = file path - where file is a tsv table with 2 columns:
                    column0: the individual ID
                    column1: bam file path relative to the base settings.READ_VIZ_BAM_PATH url or directory - so that
                        the absolute bam path can be derived by doing os.path.join(settings.READ_VIZ_BAM_PATH, column1)
        """
        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        for line in open(args[1]).readlines():
            try:
                indiv_id, bam_path = line.strip('\n').split('\t')

                if options["slugify"]:
                    indiv_id = slugify(indiv_id)
            except Exception as e:
                raise ValueError("Couldn't parse line: %s" % line, e) 
            
            try:
                indiv = Individual.objects.get(project=project, indiv_id=indiv_id)
            except ObjectDoesNotExist as e: 
                print("ERROR: Individual not found in xBrowse: '%s'. Skipping.." % indiv_id)
                continue

            #if indiv.bam_file_path == bam_path:
            #    continue
            
            print "READ_VIZ_BAM_PATH=%s" % settings.READ_VIZ_BAM_PATH

            absolute_path = os.path.join(settings.READ_VIZ_BAM_PATH, bam_path)
            print "absolute_path=%s" % absolute_path
            if absolute_path.startswith('http'):
                if absolute_path.endswith(".bam"):
                    for url_to_check in [absolute_path, absolute_path.replace(".bam", ".bai")]:
                        sys.stdout.write("Checking " + url_to_check + " ..  ")
                        response = requests.request("HEAD", url_to_check, auth=(settings.READ_VIZ_USERNAME, settings.READ_VIZ_PASSWD), verify=False)
                        if response.status_code != 200:
                            if url_to_check.endswith(".bai"):
                                alt_url = url_to_check.replace(".bai",".bam.bai")
                                sys.stdout.write("Checking " + alt_url + " ..  ")
                                response = requests.request("HEAD", url_to_check, auth=(settings.READ_VIZ_USERNAME, settings.READ_VIZ_PASSWD), verify=False)
                                if response.status_code != 200:
                                    print("ERROR: reponse code == " + str(response.status_code) + ". Skipping..")
                                    continue
                            else:
                                print("ERROR: reponse code == " + str(response.status_code) + ". Skipping..")
                                continue
                        else:
                            print("SUCCESS: reponse code == " + str(response.status_code))
            elif not os.path.isfile(absolute_path):
                print("ERROR: " + absolute_path + " not found. Skipping..")
                continue
            
            
            indiv.bam_file_path = bam_path
            indiv.save()

