from django.conf import settings
from django.core.management import BaseCommand
from settings import COVERAGE_DB
from reference_settings import exac_coverage_files
from glob import glob
from xbrowse import genomeloc
import os
import gzip
from tqdm import tqdm

def load_coverage_file(path):
    """Load the given ExAC coverage file"""
    
    print("Loading file: " + path)
    with gzip.open(path) as f:
        header = next(f).replace("#chrom", "chrom").rstrip('\n').split('\t')
        for line in f:  # tqdm(f, unit=' lines'):
            fields = line.rstrip('\n').split('\t')
            fields[2:] = map(float, fields[2:])  # covert stats to float

            values = dict(zip(header, fields))
            chrom = 'chr'+values['chrom']
            values['pos'] = int(values['pos'])
            
            xpos = genomeloc.get_single_location(chrom, values['pos'])
            values['xpos'] = xpos

            #print("Inserting " + str(values)) 
            COVERAGE_DB.exac_v3_coverage.insert(values)
            


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Loading ExAC coverage into: " + str(COVERAGE_DB))
        COVERAGE_DB.drop_collection('exac_v3_coverage')
        for path in sorted(glob(exac_coverage_files)):
            load_coverage_file(path)
        print("Finished loading. Creating index..")
        COVERAGE_DB['exac_v3_coverage'].create_index([('xpos', 1),])
        print("Finished.")
