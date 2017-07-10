from pprint import pprint
from seqr.pipelines.hail.utils.run_annotation_utils import convert_info_fields_to_expr


def get_cadd_vds(hail_context, genome_version):
    if genome_version == "37":
        cadd_snvs_vcf_path = 'gs://seqr-reference-data/GRCh37/CADD/whole_genome_SNVs.vcf.gz'
        cadd_indels_vcf_path = 'gs://seqr-reference-data/GRCh37/CADD/InDels.vcf.gz'

    elif genome_version == "38":
        cadd_snvs_vcf_path = 'gs://seqr-reference-data/GRCh38/CADD/whole_genome_SNVs.liftover.GRCh38.vcf.gz'
        cadd_indels_vcf_path = 'gs://seqr-reference-data/GRCh38/CADD/InDels.liftover.GRCh38.vcf.gz'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    cadd_vds = (
        hail_context
            .import_vcf([cadd_snvs_vcf_path, cadd_indels_vcf_path], force_bgz=True, min_partitions=1000)
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

    return cadd_vds