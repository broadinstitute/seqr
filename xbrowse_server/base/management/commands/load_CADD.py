import gzip
import pymongo
import pysam
import sys
import tqdm

from django.core.management.base import BaseCommand
from xbrowse import genomeloc
from xbrowse_server import mall
from xbrowse_server.base.models import Project
from xbrowse_server.mall import get_project_datastore

CADD_VARIANTS = pysam.TabixFile("/mongo/data/reference_data/CADD/whole_genome_SNVs.tsv.gz")
CADD_INDELS = pysam.TabixFile("/mongo/data/reference_data/CADD/InDels.tsv.gz")

def fetch(chrom, pos, ref, alt):
    if len(chrom) > 1:
        chrom = chrom.replace('chr', '')

    try:
        start = pos-1  # fetch requires 0-based start coord
        end = pos
        if len(ref) == len(alt):
            variants = CADD_VARIANTS.fetch(chrom.replace('chr', ''), start, end)
        else:
            variants = CADD_INDELS.fetch(chrom.replace('chr', ''), start, end)
    except Exception as e:
        print("ERROR: Unable to fetch %(chrom)s:%(start)s-%(end)s: %(e)s " % locals())
        return None

    for row in variants:
        cadd_chrom, cadd_pos, cadd_ref, cadd_alt, cadd_raw, cadd_phred = row.rstrip('\n').split('\t')
        if str(pos) == cadd_pos and alt == cadd_alt and ref == cadd_ref:
            #print(chrom, pos, ref, alt, cadd_phred)
            return cadd_phred
    else:
        return None


def load_from_cadd_file(cadd_file):
    """Utility function to load scores from a CADD file"""
    
    f = gzip.open(cadd_file)

    # skip header lines
    f.next()  
    header = f.next()
        
    for line in tqdm.tqdm(f):
        # Chrom  Pos     Ref     Alt     RawScore        PHRED
        chrom, pos, ref, alt, raw, phred = line.rstrip('\n').split('\t')

        xpos = genomeloc.get_xpos(chrom, int(pos))
        
        result = annotator_store.variants.update({'xpos': xpos, 'ref': ref, 'alt': alt, 'annotation.cadd_phred': {'$exists' : False} }, {'$set': {'annotation.cadd_phred': phred}}, upsert=False)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('project_id', nargs='?')
        parser.add_argument('cadd_file', nargs='?')

    def handle(self, *args, **options):
        """load CADD scores for all variants in a project, or all variants in the annotator_store."""

        annotator_store = mall.get_annotator().get_annotator_datastore()
        if options['cadd_file']:
            print("Loading " + options['cadd_file'])
            load_from_cadd_file(options['cadd_file'])
        elif options['project_id']:
            print("Loading " + options['project_id'])
            project = Project.objects.get(project_id=options['project_id'])
            variant_collection = get_project_datastore(project)._get_project_collection(options['project_id']).find({'annotation.cadd_phred': {'$exists' : False}})
        else:
            variant_collection = annotator_store.variants.find({'annotation.cadd_phred': {'$exists' : False}})

        #print("Variant collection: " + str(variant_collection))
        #print("Annotating %s variants" % variant_collection.count())

        for r in tqdm.tqdm(variant_collection, unit=' variants'): #, total=variant_collection.count()):
            chrom, pos = genomeloc.get_chr_pos(r['xpos'])
            cadd_phred = fetch(chrom, pos, r['ref'], r['alt'])
            if cadd_phred is not None:
                result = annotator_store.variants.update({'xpos': r['xpos'], 'ref': r['ref'], 'alt': r['alt']}, {'$set': {'annotation.cadd_phred': cadd_phred}}, upsert=False)
                assert result['updatedExisting']

        print("Done")
