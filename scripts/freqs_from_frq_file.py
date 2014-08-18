import argparse
import os
from xbrowse import get_xpos


description = """Convert .frq file to an xbrowse .freqs file. \
I'm not sure where the .frq file comes from, but it is used by Mitja to process Finnish frequency data.
"""

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('frq')
    args = parser.parse_args()

    filename = args.frq
    if not os.path.exists(filename):
        raise Exception('File does not exist')
    if '.' not in filename:
        raise Exception('Filename must have an extension.')
    out_filename = filename + '.xbrowse.freqs'
    outfile = open(out_filename, 'w')

    for line in open(filename):
        if line.startswith('CHROM'):
            continue
        fields = line.strip('\n').split('\t')
        xpos = get_xpos(fields[0], int(fields[1]))
        allele_af = {}
        for field in fields[4:]:
            allele, af = field.split(':')
            allele_af[allele] = float(af)
        ref_allele = max(allele_af, key=allele_af.get)
        for allele, af in allele_af.items():
            if allele != ref_allele:
                outfile.write('\t'.join([
                    str(xpos),
                    ref_allele,
                    allele,
                    str(af)
                ])+'\n')
    outfile.close()