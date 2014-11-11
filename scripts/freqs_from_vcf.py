import sys
from xbrowse.parsers.vcf_stuff import iterate_vcf
from xbrowse.utils import get_aaf


if __name__ == '__main__':

    vcf_file = open(sys.argv[1])
    for variant in iterate_vcf(vcf_file, genotypes=True):
        print '\t'.join([
            str(variant.xpos),
            variant.ref,
            variant.alt,
            str(get_aaf(variant)),
        ])