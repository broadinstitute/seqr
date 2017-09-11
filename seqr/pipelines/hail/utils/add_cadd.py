from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr

CADD_FIELDS = """
    PHRED: Double,
    RawScore: Double,
"""


def add_cadd_from_vds(hail_context, vds, genome_version, root="va.cadd", info_fields=CADD_FIELDS, verbose=True):
    """Add CADD scores to the vds"""

    if genome_version == "37":
        cadd_snvs_vds_path = 'gs://seqr-reference-data/GRCh37/CADD/whole_genome_SNVs.vds'
        cadd_indels_vds_path = 'gs://seqr-reference-data/GRCh37/CADD/InDels.vds'

    elif genome_version == "38":
        cadd_snvs_vds_path = 'gs://seqr-reference-data/GRCh38/CADD/whole_genome_SNVs.liftover.GRCh38.vds'
        cadd_indels_vds_path = 'gs://seqr-reference-data/GRCh38/CADD/InDels.liftover.GRCh38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    #cadd_vds = hail_context.import_vcf([cadd_snvs_vcf_path, cadd_indels_vcf_path], force_bgz=True, min_partitions=1000)
    cadd_vds = hail_context.read([cadd_snvs_vds_path, cadd_indels_vds_path]).split_multi()

    expr = convert_vds_schema_string_to_annotate_variants_expr(
        root=root,
        other_source_fields=info_fields,
        other_source_root="vds.info",
    )

    if verbose:
        print(expr)
        #print("\n==> cadd summary: ")
        #print("\n" + str(cadd_vds.summarize()))

    return vds.annotate_variants_vds(cadd_vds, expr=expr)
