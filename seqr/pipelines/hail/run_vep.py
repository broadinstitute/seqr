import argparse
import hail
import pprint

p = argparse.ArgumentParser()
p.add_argument("input_file", help="input vcf or vds")
p.add_argument("output_vds", help="output vds")
args = p.parse_args()

print("Input File: %s" % (args.input_file, ))
print("Output VDS: %s" % (args.output_vds, ))

#input_vcf = "gs://seqr-public/test-projects/1kg-exomes/1kg.liftover.GRCh38.vep.vcf.gz"
#input_vcf = "gs://seqr-public/test-projects/1kg-exomes/1kg.vep.vcf.gz"

hc = hail.HailContext(log="/hail.log")

if args.input_file.endswith(".vds"):
    vds = hc.read(args.input_file)
elif args.input_file.endswith("gz"):
    vds = hc.import_vcf(args.input_file, force_bgz=True, min_partitions=1000)
else:
    p.error("Invalid input file: %s" % args.input_file)

vds = vds.split_multi().vep(config="/vep/vep-gcloud.properties", root='va.vep', block_size=1000)  #, csq=True)


pprint.pprint(vds.variant_schema)

vds.write(args.output_vds, overwrite=True)
