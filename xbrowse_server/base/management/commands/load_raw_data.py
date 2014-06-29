from django.core.management.base import BaseCommand
from django.conf import settings
from xbrowse.parsers import vcf_stuff
from xbrowse.core.genomeloc import CHROMOSOMES
from xbrowse.core import genomeloc


def load_dbsnp():
    dbsnp_file = open(settings.INTERMEDIATE_FILE_DIR + 'dbsnp.tsv', 'w')
    for i, variant in enumerate(vcf_stuff.iterate_vcf(open(settings.DBSNP_VCF_FILE))):
        if not i % 100000:
            print i
        fields = [
            str(variant.xpos),
            variant.ref,
            variant.alt,
            variant.vcf_id,
        ]
        dbsnp_file.write('\t'.join(fields)+'\n')
    dbsnp_file.close()


def load_dbnsfp():

    polyphen_map = {
        'D': 'probably_damaging',
        'P': 'possibly_damaging',
        'B': 'benign',
    }

    sift_map = {
        'D': 'damaging',
        'T': 'tolerated',
    }

    fathmm_map = {
        'D': 'damaging',
        'T': 'tolerated',
    }

    muttaster_map = {
        'A': 'disease_causing',
        'D': 'disease_causing',
        'N': 'polymorphism',
        'P': 'polymorphism',
    }

    nsfp_file = open(settings.INTERMEDIATE_FILE_DIR + 'dbnsfp.tsv', 'w')
    for chrom in CHROMOSOMES:
        print "Reading dbNSFP data for {}".format(chrom)
        single_chrom_file = open(settings.DBNSFP_DIR + 'dbNSFP2.1_variant.' + chrom)
        for i, line in enumerate(single_chrom_file):
            if i == 0: continue
            fields = line.strip('\n').split('\t')
            chrom, pos, ref, alt = fields[:4]
            chrom = 'chr' + chrom
            pos = int(pos)
            xpos = genomeloc.get_single_location(chrom, pos)
            if not xpos:
                continue
            polyphen = polyphen_map.get(fields[25], '.')
            sift = sift_map.get(fields[23], '.')
            fathmm = fathmm_map.get(fields[39], '.')
            muttaster = muttaster_map.get(fields[33], '.')
            fields = [
                str(xpos),
                ref,
                alt,
                polyphen,
                sift,
                fathmm,
                muttaster
            ]
            nsfp_file.write('\t'.join(fields)+'\n')


class Command(BaseCommand):
    def handle(self, *args, **options):

        print 'Creating DBSNP file'
        create_dbsnp()

        print 'Creating DBNSFP file'
        create_dbnsfp()
