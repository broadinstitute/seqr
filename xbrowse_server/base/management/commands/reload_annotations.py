from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import mall
from datetime import date, datetime
import vcf

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if not args:
            print("Must provide at least one project_id")
            return

        for project_id in args:
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - db.variants cache"))
            project = Project.objects.get(project_id=project_id)

            for vcf_obj in project.get_all_vcf_files():
                r = vcf.VCFReader(filename=vcf_obj.path())
                if "CSQ" not in r.infos:
                    print("VCF %s isn't annotated (eg. doesn't have a CSQ)" % str(vcf_obj.path()))
                else:
                    print("Loading VCF %s with CSQ: %s" % (vcf_obj.path(), r.infos["CSQ"]))
                mall.get_annotator().add_preannotated_vcf_file(vcf_obj.path(), force=True)

        print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - db.variants cache"))
