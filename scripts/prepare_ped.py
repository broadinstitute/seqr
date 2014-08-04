import gzip
import argparse
import os
from xbrowse.utils import get_slugified_sample_id


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert any PED file to the xbrowse dialect')
    parser.add_argument('ped')
    args = parser.parse_args()

    filename = args.ped
    if not os.path.exists(filename):
        raise Exception('File does not exist')
    if '.' not in filename:
        raise Exception('Filename must have an extension.')
    out_filename = filename + '.xbrowse.ped'
    outfile = open(out_filename, 'w')

    for line in open(filename):
        fields = line.strip('\n').split('\t')
        for i in [2,3,4,5]:
            if fields[i] == '0':
                fields[i] = '.'
        for i in [0,1,2,3]:
            if fields[i] != '.':
                fields[i] = get_slugified_sample_id(fields[i])
        outfile.write('\t'.join(fields)+'\n')
    outfile.close()