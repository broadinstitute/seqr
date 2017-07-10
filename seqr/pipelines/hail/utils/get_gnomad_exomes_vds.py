from pprint import pprint
from seqr.pipelines.hail.utils.run_annotation_utils import convert_info_fields_to_expr


def get_gnomad_exomes_vds(hail_context, genome_version):
    if genome_version == "37":
        gnomad_exomes_vds_path = 'gs://gnomad-public/release-170228/gnomad.exomes.r2.0.1.sites.vds'
    elif genome_version == "38":
        gnomad_exomes_vds_path = 'gs://seqr-reference-data/GRCh38/gnomad/gnomad.exomes.r2.0.1.sites.liftover.b38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    expr = """
        va.for_seqr.was_split = va.wasSplit,
        va.for_seqr.filters = va.filters,
    """ + convert_info_fields_to_expr("""
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
        AC_SAS: Array[Int],
        AC_Male: Array[Int],
        AC_Female: Array[Int],
        AN_AFR: Int,
        AN_AMR: Int,
        AN_ASJ: Int,
        AN_EAS: Int,
        AN_FIN: Int,
        AN_NFE: Int,
        AN_OTH: Int,
        AN_SAS: Int,
        AN_Male: Int,
        AN_Female: Int,
        AF_AFR: Array[Double],
        AF_AMR: Array[Double],
        AF_ASJ: Array[Double],
        AF_EAS: Array[Double],
        AF_FIN: Array[Double],
        AF_NFE: Array[Double],
        AF_OTH: Array[Double],
        AF_SAS: Array[Double],
        AF_Male: Array[Double],
        AF_Female: Array[Double],
        Hom_AFR: Array[Int],
        Hom_AMR: Array[Int],
        Hom_ASJ: Array[Int],
        Hom_EAS: Array[Int],
        Hom_FIN: Array[Int],
        Hom_NFE: Array[Int],
        Hom_OTH: Array[Int],
        Hom_SAS: Array[Int],
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
        Hemi_SAS: Array[Int],
        Hemi_ASJ: Array[Int],
        Hemi_OTH: Array[Int],
        Hemi_FIN: Array[Int],
        Hemi_EAS: Array[Int],
    """)


    gnomad_exomes_vds = (
        hail_context.read(gnomad_exomes_vds_path)
            .split_multi()
            .annotate_variants_expr(expr)
            .annotate_variants_expr("va = select(va, for_seqr)")
    )


    #pprint.pprint(gnomad_exomes_vds.variant_schema)

    return gnomad_exomes_vds