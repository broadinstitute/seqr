import os
import settings
import requests
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
from django.core.exceptions import ObjectDoesNotExist
from collections import defaultdict



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-r", "--remove-broken-links", action="store_true", help="Update the database to disable readviz for bams that are no longer available")
        parser.add_argument("-t", "--thorough", action="store_true", help="Use GET instead of HEAD to check")
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        """Command line args:
            arg0 = project id
        """
        if not args:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(project_id=args[0])

        if not settings.READ_VIZ_BAM_PATH or not settings.READ_VIZ_BAM_PATH.startswith("http"):
            parser.exit("settings.READ_VIZ_BAM_PATH is not a url: " + settings.READ_VIZ_BAM_PATH)
            
        for project in projects:
            counters = defaultdict(int)
            for indiv in Individual.objects.filter(project=project):
                counters['total'] += 1

                bam_path = indiv.bam_file_path
                if not bam_path:
                    counters['no'] += 1
                    continue

                absolute_path = os.path.join(settings.READ_VIZ_BAM_PATH, bam_path)
                if not absolute_path.endswith(".bam"):
                    counters['broken'] += 1
                    print("==> Invalid bam path doesn't end with .bam: " + absolute_path)
                    if options["remove_broken_links"]:
                        print("==> Removing readviz from %s: %s " % (indiv.indiv_id, indiv.bam_file_path))
                        indiv.bam_file_path = ""
                        indiv.save()
                    continue
                counters['yes'] += 1

                bam_url_to_check = absolute_path
                bai_url_to_check = bam_url_to_check.replace(".bam", ".bam.bai")
                #print("Checking " + url_to_check)

                for url in [bam_url_to_check, bai_url_to_check]:
                    response = requests.request("GET" if options["thorough"] and url.endswith(".bai") else "HEAD", url, auth=(settings.READ_VIZ_USERNAME, settings.READ_VIZ_PASSWD), verify=False)
                    if response.status_code != 200:
                        if url == bam_url_to_check:
                            counters['broken'] += 1
                        print("%s: %s   is broken for sample id %s.  response code == %s %s" % (project.project_id, url, indiv.indiv_id, response.status_code, response.reason))
                        if options["remove_broken_links"]:
                            print("==> Removing readviz from %s: %s " % (indiv.indiv_id, indiv.bam_file_path))
                            indiv.bam_file_path = ""
                            indiv.save()
                    else:
                        print("%s: %s   is working for sample id %s" % (project.project_id, url, indiv.indiv_id))
                        if url == bam_url_to_check:
                            counters['working'] += 1

            if counters["yes"] > 0:
                print(project.project_id + ": %(no)d no readviz, %(yes)d yes readviz - %(broken)d are broken" % counters)
