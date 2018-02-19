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

    def handle(self, *args, **options):
        project_id = options['project_id']
        cnv_filename = options['cnv_filename']
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

                print("Loading data into project: " + project_id)
                p = Project.objects.get(project_id = project_id)
                i = list(Individual.objects.filter(project=p, indiv_id=row_dict['sample']))
                if not i:
                    print("WARNING: %s not found in project %s" % (p.project_id, row_dict['sample']))
                    continue
                else:
                    i = i[0]

                project_collection = get_project_datastore(project_id)._get_project_collection(project_id)
                family_collection = get_mall(project_id).variant_store._get_family_collection(p.project_id, i.family.family_id)

                for collection in [project_collection, family_collection]:
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
