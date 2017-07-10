from pprint import pprint

def get_g1k_phase3_vds(hail_context, genome_version):
    if genome_version == "37":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh37/1kg/1kg.wgs.phase3.20130502.GRCh37_sites.vds'
    elif genome_version == "38":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh38/1kg/1kg.wgs.phase3.20170504.GRCh38_sites.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    g1k_vds = (
        hail_context
            .read(g1k_vds_path)
            .split_multi()
            .annotate_variants_expr("""
                va.for_seqr.filters = va.filters,
                va.for_seqr.AC = va.info.AC,
                va.for_seqr.AF = va.info.AF,
                va.for_seqr.AN = va.info.AN,
                va.for_seqr.AF_EAS = va.info.EAS_AF,
                va.for_seqr.AF_EUR = va.info.EUR_AF,
                va.for_seqr.AF_AFR = va.info.AFR_AF,
                va.for_seqr.AF_AMR = va.info.AMR_AF,
                va.for_seqr.AF_SAS = va.info.SAS_AF,
                va.for_seqr.POPMAX_AF = va.info.POPMAX_AF,
                va.for_seqr.DP = va.info.DP
                """)
            .annotate_variants_expr("va = select(va, for_seqr)")
    )

    #pprint(g1k_vds.variant_schema)

    return g1k_vds