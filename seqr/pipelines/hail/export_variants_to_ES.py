# ./submit.sh export_callset_to_ES.py -g 37 gs://seqr-datasets/GRCh37/Engle_WGS/engle-macarthur-ccdd.vep.subset_DMD.vds

from pprint import pprint, pformat

import argparse
import hail

from utils.computed_fields_utils import get_expr_for_variant_id, \
    get_expr_for_vep_gene_ids_set, get_expr_for_vep_transcript_ids_set, \
    get_expr_for_orig_alt_alleles_set, get_expr_for_vep_consequence_terms_set, \
    get_expr_for_vep_sorted_transcript_consequences_array, \
    get_expr_for_worst_transcript_consequence_annotations_struct, get_expr_for_end_pos, \
    get_expr_for_xpos, get_expr_for_contig, get_expr_for_start_pos, get_expr_for_alt_allele, \
    get_expr_for_ref_allele
from utils.gcloud_utils import inputs_older_than_outputs
from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr
from utils.add_1kg_phase3 import add_1kg_phase3_data_struct
from utils.add_clinvar import add_clinvar_data_struct
from utils.add_mpc import add_mpc_data_struct
#from utils.add_exac import add_exac_data_struct
from utils.elasticsearch_utils import export_vds_to_elasticsearch

# test_dataset = "/seqr/20170704_1kg_4901368.vep.vds"
# test_dataset = "/Users/weisburd/data/seqr-datasets/20170704_1kg_4901368.vep.vds"
# test_dataset = "gs://seqr-datasets/GRCh38/20170513_APY-001_363620675/20170513_APY-001_363620675.vep.vds"
# test_dataset = "gs://seqr-datasets/GRCh38/engle_2_sample/combined-vep-APY-001.vcf.bgz"
#test_dataset = "gs://seqr-hail/test-data/combined-vep-APY-001_subset.vcf.bgz"
# test_dataset = "gs://seqr-datasets/GRCh37/Engle_WGS/engle-macarthur-ccdd.vep.vds"
#vds = hc.read("gs://seqr-datasets/GRCh37/Engle_WGS/engle-macarthur-ccdd.vep.vds").filter_intervals(hail.Interval.parse('X:31224000-31228000'))
#vds.write("gs://seqr-datasets/GRCh37/Engle_WGS/engle-macarthur-ccdd.vep.subset_DMD.vds", overwrite=True)

p = argparse.ArgumentParser()
p.add_argument("-g", "--genome-version", help="Genome build: 37 or 38", choices=["37", "38"], required=True )
#p.add_argument("-f", "--force-vep", help="Re-run VEP even the input file is already annotated. "
#    "Otherwise, VEP will be skipped if the input VDS already has a va.vep field.")
p.add_argument("-H", "--host", help="Elasticsearch host or IP", default="10.48.0.105")
p.add_argument("-p", "--port", help="Elasticsearch port", default=30001, type=int)  # 9200
p.add_argument("-i", "--index", help="Elasticsearch index name", default="variant_callset")
p.add_argument("-t", "--index-type", help="Elasticsearch index type", default="variant")
p.add_argument("-b", "--block-size", help="Elasticsearch block size", default=5000)
p.add_argument("dataset_path", help="input VCF or VDS")

# parse args
args = p.parse_args()

hc = hail.HailContext(log="/hail.log")

if args.dataset_path.endswith(".vds"):
    vds = hc.read(args.dataset_path)
else:
    vds = hc.import_vcf(args.dataset_path, force_bgz=True, min_partitions=1000)

vds = vds.annotate_variants_expr("va.originalAltAlleles=%s" % get_expr_for_orig_alt_alleles_set())
vds = vds.split_multi()

if not any(field.name == "vep" for field in vds.variant_schema.fields):
    raise ValueError("%s isn't VEP-annotated. va.vep field not found: %s" %(
        args.dataset_path, pformat(vds.variant_schema)))

    """
    vep_output_path = args.dataset_path.replace(".vds", "").replace(".vcf.gz", "").replace(".vcf.bgz", "") + ".vep.vds"
    if args.force_vep or not inputs_older_than_outputs([args.dataset_path], [vep_output_path]):
        vds = vds.vep(config="/vep/vep-gcloud.properties", root='va.vep', block_size=1000)  #, csq=True)
        vds.write(vep_output_path, overwrite=True)
    else:
        vds = vds.read(vep_output_path)
    """

#pprint(vds.variant_schema)
#pprint(vds.sample_ids)

# ./submit.sh export_callset_to_ES.py -g 37 gs://seqr-datasets/GRCh37/Engle_WGS/engle-macarthur-ccdd.vep.subset_DMD.vds

# add computed fields
vds_computed_annotations_exprs = [
    "va.geneIds = %s" % get_expr_for_vep_gene_ids_set(vep_root="va.vep"),
    "va.transcriptIds = %s" % get_expr_for_vep_transcript_ids_set(vep_root="va.vep"),
    "va.transcriptConsequenceTerms = %s" % get_expr_for_vep_consequence_terms_set(vep_root="va.vep"),
    "va.sortedTranscriptConsequences = %s" % get_expr_for_vep_sorted_transcript_consequences_array(vep_root="va.vep"),
    "va.mainTranscript = %s" % get_expr_for_worst_transcript_consequence_annotations_struct("va.sortedTranscriptConsequences"),
    "va.sortedTranscriptConsequences = json(va.sortedTranscriptConsequences)",

    "va.variantId = %s" % get_expr_for_variant_id(),

    "va.contig = %s" % get_expr_for_contig(),
    "va.start = %s" % get_expr_for_start_pos(),
    "va.pos = %s" % get_expr_for_start_pos(),
    "va.end = %s" % get_expr_for_end_pos(),
    "va.ref = %s" % get_expr_for_ref_allele(),
    "va.alt = %s" % get_expr_for_alt_allele(),

    "va.xpos = %s" % get_expr_for_xpos(pos_field="start"),
    "va.xstart = %s" % get_expr_for_xpos(pos_field="start"),
    "va.xstop = %s" % get_expr_for_xpos(field_prefix="va.", pos_field="end"),
]
for expr in vds_computed_annotations_exprs:
    vds = vds.annotate_variants_expr(expr)

# apply schema to dataset
INPUT_SCHEMA = {
    "top_level_fields": """
        contig: String,
        start: Int,
        pos: Int,
        end: Int,
        ref: String,
        alt: String,

        xpos: Long,
        xstart: Long,
        xstop: Long,

        rsid: String,
        qual: Double,
        filters: Set[String],
        wasSplit: Boolean,

        variantId: String,
        originalAltAlleles: Set[String],
        geneIds: Set[String],
        transcriptIds: Set[String],
        transcriptConsequenceTerms: Set[String],
        mainTranscript: Struct,
        sortedTranscriptConsequences: String,
    """,
    "info_fields": """
         AC: Array[Int],
         AF: Array[Double],
         AN: Int,
         BaseQRankSum: Double,
         ClippingRankSum: Double,
         DP: Int,
         DS: Boolean,
         END: Int,
         FS: Double,
         HaplotypeScore: Double,
         InbreedingCoeff: Double,
         MQ: Double,
         MQRankSum: Double,
         QD: Double,
         ReadPosRankSum: Double,
         VQSLOD: Double,
         culprit: String,
    """
}

DISABLE_INDEX_FOR_FIELDS = ("sortedTranscriptConsequences", )
DISABLE_DOC_VALUES_FOR_FIELDS = ("sortedTranscriptConsequences", )

vds = vds.annotate_variants_expr(
    convert_vds_schema_string_to_annotate_variants_expr(root="va.clean", **INPUT_SCHEMA)
)
vds = vds.annotate_variants_expr("va = va.clean")

# add reference data
vds = add_1kg_phase3_data_struct(hc, vds, args.genome_version, root="va.g1k")
vds = add_clinvar_data_struct(hc, vds, args.genome_version, root="va.clinvar")
vds = add_mpc_data_struct(hc, vds, args.genome_version, root="va.mpc")

# see https://hail.is/hail/annotationdb.html#query-builder
vds = vds.annotate_variants_db([
    'va.cadd.PHRED',
    'va.cadd.RawScore',
    'va.dann.score',
])

"""
    vds
        .annotate_variants_vds(g1k_vds, expr="va.g1k = vds.for_seqr")
        .annotate_variants_vds(exac_vds, expr="va.exac = vds.for_seqr")
        .annotate_variants_vds(gnomad_exomes_vds, expr="va.gnomad_exomes = vds.for_seqr")
        .annotate_variants_vds(gnomad_genomes_vds, expr="va.gnomad_genomes = vds.for_seqr")
        .annotate_variants_vds(clinvar_vds, expr="va.clinvar = vds.for_seqr")
        .annotate_variants_vds(mpc_vds, expr="va.mpc = vds.for_seqr")
        .annotate_variants_vds(cadd_vds, expr="va.cadd = vds.for_seqr")
"""

pprint(vds.variant_schema)
pprint(vds.sample_ids)

export_vds_to_elasticsearch(
    vds,
    export_genotypes=True,
    host=args.host,
    port=args.port,
    index_name=args.index,
    index_type_name=args.index_type,
    block_size=args.block_size,
    delete_index_before_exporting=True,
    disable_index_for_fields=DISABLE_INDEX_FOR_FIELDS,
    is_split_vds=True,
    verbose=True,
)

