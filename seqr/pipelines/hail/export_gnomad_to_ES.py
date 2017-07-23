import argparse
from utils.computed_fields_utils import get_expr_for_xpos, get_expr_for_orig_alt_alleles_set, \
    get_expr_for_variant_id, get_expr_for_vep_gene_ids_set, get_expr_for_vep_transcript_ids_set, \
    get_expr_for_vep_consequence_terms_set, get_expr_for_vep_sorted_transcript_consequences_array, \
    get_expr_for_worst_transcript_consequence_annotations_struct, get_expr_for_end_pos, \
    get_expr_for_contig, get_expr_for_start_pos, get_expr_for_alt_allele, get_expr_for_ref_allele
from utils.elasticsearch_utils import export_kt_to_elasticsearch
from utils.vds_schema_string_utils import convert_vds_schema_string_to_vds_make_table_arg

import hail
from pprint import pprint

p = argparse.ArgumentParser()
p.add_argument("-g", "--genome_version", help="Genome build: 37 or 38", choices=["37", "38"], required=True)
p.add_argument("-H", "--host", help="Elasticsearch host or IP", default="10.48.0.105")
p.add_argument("-p", "--port", help="Elasticsearch port", default=30001, type=int)  # 9200
p.add_argument("-i", "--index", help="Elasticsearch index name", default="gnomad_combined")
p.add_argument("-t", "--index-type", help="Elasticsearch index type", default="variant")
p.add_argument("-b", "--block-size", help="Elasticsearch block size", default=200)

# parse args
args = p.parse_args()

hc = hail.HailContext(log="/hail.log") #, branching_factor=1)

GNOMAD_VDS_PATHS = {
    "exomes_37": "gs://gnomad-public/release-170228/gnomad.exomes.r2.0.1.sites.vds",
    "exomes_38": "gs://seqr-reference-data/GRCh38/gnomad/gnomad.exomes.r2.0.1.sites.liftover.b38.vds",
    "genomes_37": "gs://gnomad-public/release-170228/gnomad.genomes.r2.0.1.sites.vds",
    "genomes_38": "gs://seqr-reference-data/GRCh38/gnomad/gnomad.genomes.r2.0.1.sites.liftover.b38.vds",
}


exomes_vds = hc.read(GNOMAD_VDS_PATHS["exomes_"+args.genome_version]).filter_intervals(hail.Interval.parse('22')) # hail.Interval.parse('X:31224000-31228000'))
exomes_vds.write("gs://gnomad-bw2/reference_data/GRCh37/gnomad/gnomad.exomes.r2.0.1.vep.sites_%s_chr22_subset.vds" % args.genome_version, overwrite=True)

genomes_vds = hc.read(GNOMAD_VDS_PATHS["genomes_"+args.genome_version]).filter_intervals(hail.Interval.parse('22')) #hail.Interval.parse('X:31224000-31228000'))
genomes_vds.write("gs://gnomad-bw2/reference_data/GRCh37/gnomad/gnomad.genomes.r2.0.1.vep.sites_%s_chr22_subset.vds" % args.genome_version, overwrite=True)

#exomes_vds = hc.read("gs://gnomad-bw2/reference_data/GRCh37/gnomad/gnomad.exomes.r2.0.1.vep.sites_DMD_subset.vds")
#genomes_vds = hc.read("gs://gnomad-bw2/reference_data/GRCh37/gnomad/gnomad.genomes.r2.0.1.vep.sites_DMD_subset.vds")

# based on output of pprint(vds.variant_schema)
GNOMAD_SCHEMA = {
    "top_level_fields": """
        contig: String,
        start: Int,
        ref: String,
        alt: String,

        rsid: String,
        qual: Double,
        filters: Set[String],
        wasSplit: Boolean,

        joinKey: String,
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
        FS: Double,
        InbreedingCoeff: Double,
        MQ: Double,
        MQRankSum: Double,
        QD: Double,
        ReadPosRankSum: Double,
        VQSLOD: Double,
        VQSR_culprit: String,
        GQ_HIST_ALT: Array[String],
        DP_HIST_ALT: Array[String],
        AB_HIST_ALT: Array[String],
        AC_AFR: Array[Int],
        AC_AMR: Array[Int],
        AC_ASJ: Array[Int],
        AC_EAS: Array[Int],
        AC_FIN: Array[Int],
        AC_NFE: Array[Int],
        AC_OTH: Array[Int],
        AC_Male: Array[Int],
        AC_Female: Array[Int],
        AN_AFR: Int,
        AN_AMR: Int,
        AN_ASJ: Int,
        AN_EAS: Int,
        AN_FIN: Int,
        AN_NFE: Int,
        AN_OTH: Int,
        AN_Male: Int,
        AN_Female: Int,
        AF_AFR: Array[Double],
        AF_AMR: Array[Double],
        AF_ASJ: Array[Double],
        AF_EAS: Array[Double],
        AF_FIN: Array[Double],
        AF_NFE: Array[Double],
        AF_OTH: Array[Double],
        AF_Male: Array[Double],
        AF_Female: Array[Double],
        Hom_AFR: Array[Int],
        Hom_AMR: Array[Int],
        Hom_ASJ: Array[Int],
        Hom_EAS: Array[Int],
        Hom_FIN: Array[Int],
        Hom_NFE: Array[Int],
        Hom_OTH: Array[Int],
        Hom_Male: Array[Int],
        Hom_Female: Array[Int],
        Hom: Array[Int],
        POPMAX: Array[String],
        AC_POPMAX: Array[Int],
        AN_POPMAX: Array[Int],
        AF_POPMAX: Array[Double],
        Hemi_NFE: Array[Int],
        Hemi_AFR: Array[Int],
        Hemi_AMR: Array[Int],
        Hemi: Array[Int],
        Hemi_ASJ: Array[Int],
        Hemi_OTH: Array[Int],
        Hemi_FIN: Array[Int],
        Hemi_EAS: Array[Int],
    """
}

vds_computed_annotations_exprs = [
    "va.contig = %s" % get_expr_for_contig(),
    "va.start = %s" % get_expr_for_start_pos(),
    "va.ref = %s" % get_expr_for_ref_allele(),
    "va.alt = %s" % get_expr_for_alt_allele(),
    "va.joinKey = %s" % get_expr_for_variant_id(),
    "va.variantId = %s" % get_expr_for_variant_id(),
    "va.originalAltAlleles = %s" % get_expr_for_orig_alt_alleles_set(),
    "va.geneIds = %s" % get_expr_for_vep_gene_ids_set(),
    "va.transcriptIds = %s" % get_expr_for_vep_transcript_ids_set(),
    "va.transcriptConsequenceTerms = %s" % get_expr_for_vep_consequence_terms_set(),
    "va.sortedTranscriptConsequences = %s" % get_expr_for_vep_sorted_transcript_consequences_array(),
    "va.mainTranscript = %s" % get_expr_for_worst_transcript_consequence_annotations_struct("va.sortedTranscriptConsequences"),
    "va.sortedTranscriptConsequences = json(va.sortedTranscriptConsequences)",
]


print("======== Exomes: KT Schema ========")
exomes_vds = exomes_vds.annotate_variants_expr("va.exomes.originalAltAlleles=%s" % get_expr_for_orig_alt_alleles_set())
exomes_vds = exomes_vds.split_multi()
for expr in vds_computed_annotations_exprs:
    exomes_vds = exomes_vds.annotate_variants_expr(expr)
exomes_kt_variant_expr = convert_vds_schema_string_to_vds_make_table_arg(output_field_name_prefix="exomes_", **GNOMAD_SCHEMA)
exomes_kt = exomes_vds.make_table(exomes_kt_variant_expr, [])
pprint(exomes_kt.schema)

print("======== Genomes: KT Schema ========")
genomes_vds = genomes_vds.annotate_variants_expr("va.genomes.originalAltAlleles=%s" % get_expr_for_orig_alt_alleles_set())
genomes_vds = genomes_vds.split_multi()
for expr in vds_computed_annotations_exprs:
    genomes_vds = genomes_vds.annotate_variants_expr(expr)
genomes_kt_variant_expr = convert_vds_schema_string_to_vds_make_table_arg(output_field_name_prefix="genomes_", **GNOMAD_SCHEMA)
genomes_kt = genomes_vds.make_table(genomes_kt_variant_expr, [])
pprint(genomes_kt.schema)

print("======== Combined: KT Schema ======")
combined_kt = genomes_kt.key_by("genomes_joinKey").join(exomes_kt.key_by("exomes_joinKey"), how="outer")
combined_kt = combined_kt.drop(["genomes_joinKey"])

for field in [
    "contig", "start", "ref", "alt", "variantId", "rsid",
    "geneIds", "transcriptIds",
    "transcriptConsequenceTerms", "sortedTranscriptConsequences", "mainTranscript"
]:
    combined_kt = combined_kt.annotate("%(field)s = orElse( exomes_%(field)s, genomes_%(field)s )" % locals())
    combined_kt = combined_kt.drop(["exomes_"+field, "genomes_"+field])

combined_kt = combined_kt.annotate("pos = start")
combined_kt = combined_kt.annotate("stop = %s" % get_expr_for_end_pos(field_prefix="", pos_field="start", ref_field="ref"))
combined_kt = combined_kt.annotate("xpos = %s" % get_expr_for_xpos(field_prefix="", pos_field="start"))
combined_kt = combined_kt.annotate("xstart = %s" % get_expr_for_xpos(field_prefix="", pos_field="start"))
combined_kt = combined_kt.annotate("xstop = %s" % get_expr_for_xpos(field_prefix="", pos_field="stop"))

# flatten and prune mainTranscript
transcript_annotations_to_keep = [
    "amino_acids",
    "biotype",
    "canonical",
    "cdna_start",
    "cdna_end",
    "codons",
    #"distance",
    "domains",
    "exon",
    "gene_id",
    "gene_symbol",
    "gene_symbol_source",
    "hgnc_id",
    "hgvsc",
    "hgvsp",
    "lof",
    "lof_flags",
    "lof_filter",
    "lof_info",
    "protein_id",
    "transcript_id",

    "hgvs",
    "major_consequence",
    "major_consequence_rank",
    "category",
]

for field_name in transcript_annotations_to_keep:
    new_field_name = "mainTranscript." + "".join(map(lambda word: word.capitalize(), field_name.split("_")))
    combined_kt = combined_kt.annotate("%(new_field_name)s = mainTranscript.%(field_name)s" % locals())

combined_kt = combined_kt.drop(["mainTranscript"])

pprint(combined_kt.schema)

DISABLE_INDEX_AND_DOC_VALUES_FOR_FIELDS = ("sortedTranscriptConsequences", )

print("======== Export to elasticsearch ======")
export_kt_to_elasticsearch(
    combined_kt,
    host=args.host,
    port=args.port,
    index_name=args.index,
    index_type_name=args.index_type,
    block_size=args.block_size,
    delete_index_before_exporting=True,
    disable_doc_values_for_fields=DISABLE_INDEX_AND_DOC_VALUES_FOR_FIELDS,
    disable_index_for_fields=DISABLE_INDEX_AND_DOC_VALUES_FOR_FIELDS,
    verbose=True,
)


