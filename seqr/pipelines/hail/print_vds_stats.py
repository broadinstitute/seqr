import argparse
import hail
import os
import sys

hc = hail.HailContext()

# exac, gnomad, 1kg, clinvar, cadd

p = argparse.ArgumentParser()
p.add_argument("input_path", help="input VCF or VDS")
args = p.parse_args()
input_path = args.input_path

print("Input path: %s" % input_path)

if input_path.endswith(".vds"):
    vds = hc.read(input_path)
else:
    vds = hc.import_vcf(input_path, min_partitions=1000, force_bgz=True)

print(vds.sample_schema)
print(vds.variant_schema)
print(vds.genotype_schema)
print(vds.split_multi().count())
