

def add_1kg_phase3_data_struct(hail_context, vds, genome_version, root="va.g1k"):
    """Add 1000 genome AC and AF annotations to the vds"""

    if genome_version == "37":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh37/1kg/1kg.wgs.phase3.20130502.GRCh37_sites.vds'
    elif genome_version == "38":
        g1k_vds_path = 'gs://seqr-reference-data/GRCh38/1kg/1kg.wgs.phase3.20170504.GRCh38_sites.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    g1k_vds = hail_context.read(g1k_vds_path).split_multi()

    return vds.annotate_variants_vds(g1k_vds,
        expr="""
            %(root)s.AC = vds.g1k.AC,
            %(root)s.AF = vds.g1k.AF,
            %(root)s.EAS_AF = vds.g1k.EAS_AF,
            %(root)s.EUR_AF = vds.g1k.EUR_AF,
            %(root)s.AFR_AF = vds.g1k.AFR_AF,
            %(root)s.AMR_AF = vds.g1k.AMR_AF,
            %(root)s.SAS_AF = vds.g1k.SAS_AF,
            %(root)s.POPMAX_AF = vds.g1k.POPMAX_AF
        """ % locals())
