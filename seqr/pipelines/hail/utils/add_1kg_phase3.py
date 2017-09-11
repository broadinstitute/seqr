from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr

G1K_FIELDS = """
    AC: Int,
    AF: Float,
    EAS_AF: Float,
    EUR_AF: Float,
    AFR_AF: Float,
    AMR_AF: Float,
    SAS_AF: Float,
    POPMAX_AF: Float,
"""

def add_1kg_phase3_from_vds(hail_context, vds, genome_version, root="va.g1k", fields=G1K_FIELDS, verbose=True):
    """Add 1000 genome AC and AF annotations to the vds"""

    if genome_version == "37":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh37/1kg/1kg.wgs.phase3.20130502.GRCh37_sites.vds'
    elif genome_version == "38":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh38/1kg/1kg.wgs.phase3.20170504.GRCh38_sites.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    g1k_vds = hail_context.read(g1k_vds_path).split_multi()

    expr = convert_vds_schema_string_to_annotate_variants_expr(
        root=root,
        other_source_fields=fields,
        other_source_root="vds.g1k",
    )

    if verbose:
        print(expr)
        #print("\n==> 1kg summary: ")
        #print("\n" + str(g1k_vds.summarize()))

    return vds.annotate_variants_vds(g1k_vds, expr=expr)
