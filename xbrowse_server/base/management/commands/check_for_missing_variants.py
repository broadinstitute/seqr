from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse import vcf_stuff
import gzip
from xbrowse_server.mall import get_mall
import os

class Command(BaseCommand):
    def handle(self, *args, **options):
        if not args:
            args = [p.project_id for p in Project.objects.all()]
            args.reverse()

        for project_id in args:
            #print("Processing project " + project_id)
            try:
                project = Project.objects.get(project_id=project_id)
            except:
                print("ERROR: Project not found. Skipping..")
                continue
            all_counter = 0
            #found_counter = 0
            not_found_counter = 0
            not_found_variants = []
            for vcf_file in project.get_all_vcf_files():
                path = vcf_file.file_path
                #print("Processing %s - %s" % (project.project_id, path))
                if not os.path.isfile(path) and path.endswith(".vcf"):
                    path = path + ".gz"
                if path.endswith(".gz"):
                    f = gzip.open(path)
                else:
                    f = open(path)
                if f:
                    for variant in vcf_stuff.iterate_vcf(f):
                        all_counter += 1
                        try:
                            get_mall().annotator.get_annotation(variant.xpos, variant.ref, variant.alt)
                        except ValueError, e:
                            not_found_counter += 1
                            if len(not_found_variants) < 10:
                                not_found_variants.append((variant.xpos, variant.ref, variant.alt))
                            #print("WARNING: variant not found in annotator cache: " + str(e))
                            #if not_found_counter > 5:
                            #    print("---- ERROR: 5 variants not found. Project %s should be reloaded." % project_id)
                            #    break
                            found_counter = 0
                        #else:
                        #    found_counter += 1
                        #    if found_counter > 15000:
                        #        #print("---- Found 5000 variants in a row. Project %s looks ok." % project_id)
                        #        break
                        if all_counter >= 20000:
                            fraction_missing = float(not_found_counter) / all_counter
                            if not_found_counter > 10:
                                print("---- ERROR: (%(fraction_missing)0.2f%%)  %(not_found_counter)s / %(all_counter)s variants not found. Project %(project_id)s should be reloaded. Examples: %(not_found_variants)s" % locals())
                            break
