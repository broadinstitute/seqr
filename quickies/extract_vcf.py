from base import *

import sys

import argparse
from xbrowse.parsers import vcf_stuff
from xbrowse.utils import is_variant_relevant_for_individuals
from xbrowse.core import displays


parser = argparse.ArgumentParser()
parser.add_argument("vcf_file")
parser.add_argument("indiv_id_file")
args = parser.parse_args()
vcf_file_path = args.vcf_file
indivs_to_include = list(i.strip() for i in list(open(args.indiv_id_file)))
indivs_to_include_set = set(indivs_to_include)
vcf_headers = None
num_vcf_cols = None
cols_to_include = None

for _line in open(vcf_file_path):
    line = _line.strip('\n')
    fields = line.split('\t')

    if line.startswith('##'):
        print line

    elif line.startswith('#CHROM'):
        vcf_headers = vcf_stuff.get_vcf_headers(line)
        num_vcf_cols = len(vcf_headers)
        cols_to_include = {i: True for i in range(num_vcf_cols)}

        new_header_fields = vcf_headers[:9]
        for i in range(9, num_vcf_cols):
            f = vcf_headers[i]
            if f in indivs_to_include_set:
                new_header_fields.append(f)
            else:
                cols_to_include[i] = False

        print "\t".join(new_header_fields)

        # make sure VCF actually contains samples
        for indiv_id in indivs_to_include:
            if indiv_id not in vcf_headers:
                sys.stderr.write("Error: {} not in VCF file".format(indiv_id))

    else:
        variants = vcf_stuff.get_variants_from_vcf_fields(fields)
        for j, variant in enumerate(variants):
            vcf_stuff.set_genotypes_from_vcf_fields(fields, variant, j, vcf_headers, indivs_to_include=indivs_to_include_set)
        relevant = any(is_variant_relevant_for_individuals(variant, indivs_to_include) for variant in variants)
        if relevant:
           new_fields = [fields[i] for i in range(num_vcf_cols) if cols_to_include[i]]
           print '\t'.join(new_fields)