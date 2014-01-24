import sys
from xbrowse.parsers.vcf_stuff import iterate_vcf_path
from xbrowse.utils import get_aaf


if __name__ == '__main__':

    for variant in iterate_vcf_path(sys.argv[1], genotypes=True):
        print '\t'.join([
            str(variant.xpos),
            variant.ref,
            variant.alt,
            str(get_aaf(variant)),
        ])