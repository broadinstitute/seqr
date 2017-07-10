
def convert_info_fields_to_expr(info_fields):
    key_type_pairs = [field.strip().split(": ") for field in info_fields.split(',') if field.strip()]
    exprs = []
    for key, t in key_type_pairs:
        exprs.append(
            ("va.for_seqr.%(key)s = va.info.%(key)s") % locals() +
            ("[va.aIndex - 1]" if t.startswith("Array") else ""))
    return ",\n".join(exprs)



# TODO figure out why this doesn't work for the base VCF
info_fields_expr = convert_info_fields_to_expr("""
         AC: Array[Int],
         AF: Array[Double],
         AN: Int,
         BaseQRankSum: Double,
         DP: Int,
         DS: Boolean,
         FS: Double,
         HaplotypeScore: Double,
         InbreedingCoeff: Double,
         MQ: Double,
         MQ0: Int,
         MQRankSum: Double,
         QD: Double,
         ReadPosRankSum: Double,
         VQSLOD: Double,
         culprit: String,
    """)

expr = """
    va.for_seqr.rsid = va.rsid,
    va.for_seqr.qual = va.qual,
    va.for_seqr.filters = va.filters,
    va.for_seqr.info.CSQ = va.info.CSQ,
""" + info_fields_expr
