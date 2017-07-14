from seqr.pipelines.hail.utils.run_annotation_utils import convert_vds_variant_schema_to_annotate_variants_expr

VDS_PATHS = {
    "exomes_37": "gs://gnomad-public/release-170228/gnomad.exomes.r2.0.1.sites.vds",
    "exomes_38": "gs://seqr-reference-data/GRCh38/gnomad/gnomad.exomes.r2.0.1.sites.liftover.b38.vds",
    "genomes_37": "gs://gnomad-public/release-170228/gnomad.genomes.r2.0.1.sites.vds",
    "genomes_38": "gs://seqr-reference-data/GRCh38/gnomad/gnomad.genomes.r2.0.1.sites.liftover.b38.vds",
}


def get_gnomad_vds(hail_context, genome_version, exomes_or_genomes):

    if genome_version not in ("37", "38"):
        raise ValueError("Invalid genome_version: %s. Must be '37' or '38'" % str(genome_version))

    if exomes_or_genomes not in ("exomes", "genomes"):
        raise ValueError("Invalid genome_version: %s. Must be 'exomes' or 'genomes'" % str(genome_version))

    gnomad_vds_path = VDS_PATHS["%s_%s" % (exomes_or_genomes, genome_version)]

    return (
        hail_context.read(gnomad_vds_path)
            .split_multi()
            .annotate_variants_expr( convert_vds_variant_schema_to_annotate_variants_expr(
                top_level_fields="""
                    filters: Set[String],
                    rsid: String,
                    qual: Double,
                    pass: Boolean,
                    variant_class: String,
                    wasSplit: Boolean,
                    """,
                info_fields="""
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
                """))
            .annotate_variants_expr("va = select(va, clean)")
    )
