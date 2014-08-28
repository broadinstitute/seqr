import gzip
import argparse
from xbrowse.parsers import vcf_stuff


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create a CSV from the ClinVar VCF file that can go into a pandas dataframe')
    parser.add_argument('vcf')
    args = parser.parse_args()
    for variant in vcf_stuff.iterate_vcf(gzip.open(args.vcf)):
        fields = [
            str(variant.xpos),
            variant.ref,
            variant.alt
        ]
        print '\t'.join(fields)