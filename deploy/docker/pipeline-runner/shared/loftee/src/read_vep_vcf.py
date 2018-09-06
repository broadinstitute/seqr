__author__ = 'konradjk'

import argparse
import gzip
import re
import sys


def main(args):
    f = gzip.open(args.vcf) if args.vcf.endswith('.gz') else open(args.vcf)
    vep_field_names = None
    header = None
    for line in f:
        line = line.strip()

        # Reading header lines to get VEP and individual arrays
        if line.startswith('#'):
            line = line.lstrip('#')
            if line.find('ID=CSQ') > -1:
                vep_field_names = line.split('Format: ')[-1].strip('">').split('|')
            if line.startswith('CHROM'):
                header = line.split()
                header = dict(zip(header, range(len(header))))
            continue

        if vep_field_names is None:
            print >> sys.stderr, "VCF file does not have a VEP header line. Exiting."
            sys.exit(1)
        if header is None:
            print >> sys.stderr, "VCF file does not have a header line (CHROM POS etc.). Exiting."
            sys.exit(1)

        # Pull out annotation info from INFO and ALT fields
        fields = line.split('\t')
        info_field = dict([(x.split('=', 1)) if '=' in x else (x, x) for x in re.split(';(?=\w)', fields[header['INFO']])])

        # Only reading lines with an annotation after this point
        if 'CSQ' not in info_field: continue
        annotations = [dict(zip(vep_field_names, x.split('|'))) for x in info_field['CSQ'].split(',') if len(vep_field_names) == len(x.split('|'))]
        lof_annotations = [x for x in annotations if x['LoF'] == 'HC']

        # Code to process annotations and VCF line goes here...

        # annotations = list of dicts, each corresponding to a transcript-allele pair
        # (each dict in annotations contains keys from vep_field_names)
        # lof_annotations = list of dicts, only high-confidence LoF
        # if len(lof_annotations) > 0 can determine if at least one allele is LoF for at least one transcript
        # fields = vcf line, can be accessed using:
        # fields[header['CHROM']] for chromosome,
        # fields[header['ALT']] for alt allele,
        # or samples using sample names, as fields[header['sample1_name']]

    f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--vcf', '--input', '-i', help='Input VCF file (from VEP+LoF); may be gzipped', required=True)
    args = parser.parse_args()
    main(args)