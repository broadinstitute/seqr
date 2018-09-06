__author__ = 'konradjk'

import gzip
import argparse

def main(args):
    f = gzip.open(args.vcf) if args.vcf.endswith('.gz') else open(args.vcf)
    g = gzip.open(args.output, 'w') if args.output.endswith('.gz') else open(args.output, 'w')

    for line in f:
        if line.startswith('##'):
            g.write(line)
        else:
            fields = line.strip().split('\t')[:9]
            g.write('\t'.join(fields) + '\n')
    f.close()
    g.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--vcf', '--input', '-i', help='Input VCF file; may be gzipped', required=True)
    parser.add_argument('--output', '-o', help='Output file, may be gzipped if ends in .gz', required=True)
    args = parser.parse_args()
    main(args)