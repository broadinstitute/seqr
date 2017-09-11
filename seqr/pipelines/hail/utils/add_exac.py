from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr


TOP_LEVEL_FIELDS = """
    rsid: String,
    qual: Double,
    filters: Set[String],
    wasSplit: Boolean,
"""

INFO_FIELDS = """
    AC: Array[Int],
    AC_AFR: Array[Int],
    AC_AMR: Array[Int],
    AC_Adj: Array[Int],
    AC_EAS: Array[Int],
    AC_FIN: Array[Int],
    AC_Hemi: Array[Int],
    AC_Het: Array[Int],
    AC_Hom: Array[Int],
    AC_NFE: Array[Int],
    AC_OTH: Array[Int],
    AC_SAS: Array[Int],
    AF: Array[Double],
    AN: Int,
    AN_AFR: Int,
    AN_AMR: Int,
    AN_Adj: Int,
    AN_EAS: Int,
    AN_FIN: Int,
    AN_NFE: Int,
    AN_OTH: Int,
    AN_SAS: Int,
    BaseQRankSum: Double,
    ClippingRankSum: Double,
    DP: Int,
    DS: Boolean,
    FS: Double,
    GQ_MEAN: Double,
    GQ_STDDEV: Double,
    HWP: Double,
    HaplotypeScore: Double,
    Hemi_AFR: Array[Int],
    Hemi_AMR: Array[Int],
    Hemi_EAS: Array[Int],
    Hemi_FIN: Array[Int],
    Hemi_NFE: Array[Int],
    Hemi_OTH: Array[Int],
    Hemi_SAS: Array[Int],
    Het_AFR: Array[Int],
    Het_AMR: Array[Int],
    Het_EAS: Array[Int],
    Het_FIN: Array[Int],
    Het_NFE: Array[Int],
    Het_OTH: Array[Int],
    Het_SAS: Array[Int],
    Hom_AFR: Array[Int],
    Hom_AMR: Array[Int],
    Hom_EAS: Array[Int],
    Hom_FIN: Array[Int],
    Hom_NFE: Array[Int],
    Hom_OTH: Array[Int],
    Hom_SAS: Array[Int],
    InbreedingCoeff: Double,
    MLEAC: Array[Int],
    MLEAF: Array[Double],
    MQ: Double,
    MQ0: Int,
    MQRankSum: Double,
    QD: Double,
    ReadPosRankSum: Double,
    VQSLOD: Double,
    culprit: String,
    DP_HIST: Array[String],
    GQ_HIST: Array[String],
    DOUBLETON_DIST: Array[String],
    AC_MALE: Array[String],
    AC_FEMALE: Array[String],
    AN_MALE: String,
    AN_FEMALE: String,
    AC_CONSANGUINEOUS: Array[String],
    AN_CONSANGUINEOUS: String,
    Hom_CONSANGUINEOUS: Array[String],
    """

def add_exac_from_vds(hail_context, vds, genome_version, root="va.exac", top_level_fields=TOP_LEVEL_FIELDS, info_fields=INFO_FIELDS, verbose=True):
    if genome_version == "37":
        exac_vds_path = 'gs://seqr-reference-data/GRCh37/gnomad/ExAC.r1.sites.vds'
    elif genome_version == "38":
        exac_vds_path = 'gs://seqr-reference-data/GRCh38/gnomad/ExAC.r1.sites.liftover.b38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    exac_vds = hail_context.read(exac_vds_path).split_multi()

    top_fields_expr = convert_vds_schema_string_to_annotate_variants_expr(
        root=root,
        other_source_fields=top_level_fields,
        other_source_root="vds",
    )
    if verbose:
        print(top_fields_expr)

    info_fields_expr = convert_vds_schema_string_to_annotate_variants_expr(
        root=root,
        other_source_fields=info_fields,
        other_source_root="vds.info",
    )
    if verbose:
        print(info_fields_expr)

    return (vds
        .annotate_variants_vds(exac_vds, expr=top_fields_expr)
        .annotate_variants_vds(exac_vds, expr=info_fields_expr)
    )
