"""
1000 genomes sites VCF schema:

Struct {
    rsid: String,
    qual: Double,
    filters: Set[String],
    info: Struct {
        CIEND: Array[Int],
        CIPOS: Array[Int],
        CS: String,
        END: Int,
        IMPRECISE: Boolean,
        MC: Array[String],
        MEINFO: Array[String],
        MEND: Int,
        MLEN: Int,
        MSTART: Int,
        SVLEN: Array[Int],
        SVTYPE: String,
        TSD: String,
        AC: Array[Int],
        AF: Array[Double],
        NS: Int,
        AN: Int,
        EAS_AF: Array[Double],
        EUR_AF: Array[Double],
        AFR_AF: Array[Double],
        AMR_AF: Array[Double],
        SAS_AF: Array[Double],
        DP: Int,
        AA: String,
        VT: Array[String],
        EX_TARGET: Boolean,
        MULTI_ALLELIC: Boolean,
        OLD_VARIANT: String
    }
}
"""

import hail
import re

hc = hail.HailContext()

input_vcfs = [
    "gs://seqr-hail/reference_data/GRCh37/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.bgz",
    "gs://seqr-hail/reference_data/GRCh38/1kg/ALL.GRCh38_sites.20170504.vcf.bgz"
]

FIELDS_TO_KEEP = ["AC", "AF", "EAS_AF", "EUR_AF", "AFR_AF", "AMR_AF", "SAS_AF"]
for input_vcf in input_vcfs:
    output_path = re.sub(".vcf.b?gz", "", input_vcf) + ".vds"

    vds = hc.import_vcf(input_vcf, min_partitions=1000, force_bgz=True)
    print(vds.variant_schema)

    vds = vds.split_multi()

    expr =  ["va.info.%(field)s = va.info.%(field)s[ va.aIndex - 1 ]" % (field, field) for field in FIELDS_TO_KEEP]
    expr += ["va.info.POPMAX_AF = [ va.g1k.AMR_AF, va.g1k.EAS_AF, va.info.EUR_AF, va.info.SAS_AF, va.info.AFR_AF ].max()"]
    vds = vds.annotate_variants_expr(expr)

    print("Writing out VDS: " + output_path)
    print(vds.variant_schema)
    vds.write(output_path, overwrite=True)
