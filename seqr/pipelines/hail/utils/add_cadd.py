
def add_cadd_data_struct(hail_context, vds, genome_version, root="va.cadd"):
    """Add CADD scores to the vds"""

    if genome_version == "37":
        cadd_snvs_vcf_path = 'gs://seqr-reference-data/GRCh37/CADD/whole_genome_SNVs.vcf.gz'
        cadd_indels_vcf_path = 'gs://seqr-reference-data/GRCh37/CADD/InDels.vcf.gz'

    elif genome_version == "38":
        cadd_snvs_vcf_path = 'gs://seqr-reference-data/GRCh38/CADD/whole_genome_SNVs.liftover.GRCh38.vcf.gz'
        cadd_indels_vcf_path = 'gs://seqr-reference-data/GRCh38/CADD/InDels.liftover.GRCh38.vcf.gz'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    cadd_vds = hail_context.import_vcf([cadd_snvs_vcf_path, cadd_indels_vcf_path], force_bgz=True, min_partitions=1000)

    return vds.annotate_variants_vds(cadd_vds,
        expr="""
            %(root)s.filters = vds.filters,
            %(root)s.AC = vds.info.AC,
            %(root)s.AF = va.info.AF,
            %(root)s.AN = va.info.AN,
            %(root)s.AF_EAS = va.info.EAS_AF,
            %(root)s.AF_EUR = va.info.EUR_AF,
            %(root)s.AF_AFR = va.info.AFR_AF,
            %(root)s.AF_AMR = va.info.AMR_AF,
            %(root)s.AF_SAS = va.info.SAS_AF,
            %(root)s.POPMAX_AF = va.info.POPMAX_AF,
            %(root)s.DP = va.info.DP
        """ % locals())
