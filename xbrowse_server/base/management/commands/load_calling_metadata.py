import os
import sys
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual

def load_hs_metrics(indiv, hs_metrics_file):
    header = None
    for line in open(hs_metrics_file):
        line = line.rstrip('\n')
        if not line or line.startswith("#"): 
            continue
        fields = line.split("\t")
        if header is None:
            header = fields
        else:
            hs_metrics = dict(zip(header, fields))
            break
    else:
        raise ValueError("Couldn't parse file: " + hs_metrics_file)

    indiv.mean_target_coverage = float(hs_metrics['MEAN_TARGET_COVERAGE'])
    if indiv.mean_target_coverage < 95:
        indiv.coverage_status = 'I'
    else:
        indiv.coverage_status = 'C'
    indiv.save()
    print("%s mean target coverage: %0.2f"  % (indiv.indiv_id, float(hs_metrics['MEAN_TARGET_COVERAGE'])))
        
        
def load_metadata(project_id, metadata_file_path):
    print("Loading %s: %s " % (project_id, metadata_file_path))

    project = Project.objects.get(project_id=project_id)

    indiv_id_to_fields = {}
    for line in open(metadata_file_path):
        fields = line.rstrip('\n').split('\t')
        indiv_id = fields[1].replace(' ', '')
        indiv_id_to_fields[indiv_id] = fields

    for indiv in Individual.objects.filter(project=project):
        if indiv.indiv_id in indiv_id_to_fields:
            hs_metrics_file = os.path.join(os.path.dirname(metadata_file_path), "hybrid_selection_metrics", indiv.indiv_id + ".hybrid_selection_metrics")
            if not os.path.isfile(hs_metrics_file):
                print("ERROR: missing file %s: %s" % (indiv.indiv_id, hs_metrics_file))
            else:    
                load_hs_metrics(indiv, hs_metrics_file)
        else:
            print("ERROR: individual %s not found in calling metadata file: %s" % (indiv.indiv_id, metadata_file_path))
    


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+', help="Path of Picard *.calling_metadata.txt file for this project")
        parser.add_argument('-i', '--project-id', help="Project id", required=True)

    def handle(self, *args, **options):
        print(args)
        project_id = options['project_id']
        metadata_file = args[0]

        if not os.path.isfile(metadata_file):
            sys.exit("File not found: " + metadata_file)
        
        load_metadata(project_id, metadata_file)
