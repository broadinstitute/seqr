import gzip
import argparse


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert a VCF file to one that can be processed by xbrowse. Replaces IDs with slugs and zips')
    parser.add_argument('vcf')
    args = parser.parse_args()

    if args.vcf.endswith('.vcf.gz'):
        f = gzip.open(args.vcf)
        basename = args.vcf[:-7]
    elif args.vcf.endswith('.vcf'):
        f = open(args.vcf)
        basename = args.vcf[:-4]
    else:
        raise Exception('Invalid name')

    outfile = gzip.open(basename + '.xbrowse.vcf.gz', 'wb')
    for line in f:
        if line.startswith('#') and not line.startswith('##'):
            line = line.replace('.', '-')
            line = line.replace('/', '-')
            line = line.replace(':', '_')
        outfile.write(line)
    outfile.close()
