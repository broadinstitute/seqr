import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual

from xbrowse_server.mall import get_mall, get_project_datastore
from xbrowse import genomeloc


class Command(BaseCommand):
    """Command for loading .tsv files computed from PennCNV calls"""
    
    def add_arguments(self, parser):
        parser.add_argument('project_id', help="project_id")
        parser.add_argument('cnv_filename', help="cnv_filename")
        parser.add_argument('bed_files_directory', help="bed_files_directory")

    def handle(self, *args, **options):
        project_id = options['project_id']
        print("Loading data into project: " + project_id)
        project = Project.objects.get(project_id = project_id)

        cnv_filename = options['cnv_filename']
        bed_files_directory = options['bed_files_directory']
        
        if not os.path.isfile(cnv_filename):
            raise ValueError("CNV file %s doesn't exist" % options['cnv_filename'])
        
        with open(cnv_filename) as f:
            header_fields = f.readline().rstrip('\n').split('\t')
            for line in f:
                fields = line.rstrip('\n').split('\t')
                row_dict = dict(zip(header_fields, fields))

                chrom = "chr"+row_dict['chr']
                start = int(row_dict['start'])
                end = int(row_dict['end'])
                #left_overhang = int(row_dict['left_overhang_start'])
                #right_overhang = int(row_dict['right_overhang_end'])

                sample_id = row_dict['sample']
                try:
                    i = Individual.objects.get(project=project, indiv_id__istartswith=sample_id)
                except Exception as e:
                    print("WARNING: %s: %s not found in %s" % (e, sample_id, project))
                    continue
                
                bed_file_path = os.path.join(bed_files_directory, "%s.bed" % sample_id)
                if not os.path.isfile(bed_file_path):
                    print("WARNING: .bed file not found: " + bed_file_path)

                    if i.cnv_bed_file != bed_file_path:
                        print("Setting cnv_bed_file path to %s" % bed_file_path)
                        i.cnv_bed_file = bed_file_path
                        i.save()
                
                project_collection = get_project_datastore(project)._get_project_collection(project_id)
                family_collection = get_mall(project).variant_store._get_family_collection(project_id, i.family.family_id)

                for collection in filter(None, [project_collection, family_collection]):
                    
                    collection.update_many(
                        {'$and': [
                            {'xpos': {'$gte': genomeloc.get_single_location(chrom, start)} },
                            {'xpos': {'$lte': genomeloc.get_single_location(chrom, end)}}
                        ]},
                        {'$set': {'genotypes.%s.extras.cnvs' % i.indiv_id: row_dict}})

                    #result = list(collection.find({'$and' : [
                    #       {'xpos': {'$gte':  genomeloc.get_single_location(chrom, start)}},
                    #       {'xpos' :{'$lte': genomeloc.get_single_location(chrom, end)}}]},
                    #   {'genotypes.%s.extras.cnvs' % i.indiv_id :1 }))
                    #print(chrom, start, end, len(result), result[0] if result else None)

        print("Done")
