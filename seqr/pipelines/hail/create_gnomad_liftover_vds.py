"""
gnomAD sites VCF schema:

"""

import hail
import re

hc = hail.HailContext()

input_vcfs = [
    #"gs://seqr-hail/reference_data/GRCh38/gnomad/ExAC.r1.sites.liftover.b38.vcf.bgz",
    #"gs://seqr-hail/reference_data/GRCh38/gnomad/gnomad.exomes.r2.0.1.sites.liftover.b38.vcf.bgz",
    "gs://seqr-hail/reference_data/GRCh38/gnomad/gnomad.genomes.r2.0.1.sites.coding.autosomes_and_X.vcf.bgz",
    "gs://seqr-hail/reference_data/GRCh37/gnomad/ExAC.r1.sites.vep.vcf.bgz",
]

for input_vcf in input_vcfs:
    output_path = re.sub(".vcf.b?gz", "", input_vcf) + ".vds"

    vds = hc.import_vcf(input_vcf, min_partitions=10000, force_bgz=True)

    output_path = output_path.replace(".vep", "")
    print("Writing out VDS: " + output_path)
    print(vds.variant_schema)
    vds.write(output_path, overwrite=True)


"""
Schema for gs://seqr-hail/reference_data/GRCh38/gnomad/ExAC.r1.sites.liftover.b38.vcf.bgz:

Struct {
    rsid: String,
    qual: Double,
    filters: Set[String],
    info: Struct {
        AC: Array[Int],
        AC_AFR: Array[Int],
        AC_AMR: Array[Int],
        AC_Adj: Array[Int],
        AC_CONSANGUINEOUS: Array[String],
        AC_EAS: Array[Int],
        AC_FEMALE: Array[String],
        AC_FIN: Array[Int],
        AC_Hemi: Array[Int],
        AC_Het: Array[Int],
        AC_Hom: Array[Int],
        AC_MALE: Array[String],
        AC_NFE: Array[Int],
        AC_OTH: Array[Int],
        AC_POPMAX: Array[String],
        AC_SAS: Array[Int],
        AF: Array[Double],
        AGE_HISTOGRAM_HET: Array[String],
        AGE_HISTOGRAM_HOM: Array[String],
        AN: Int,
        AN_AFR: Int,
        AN_AMR: Int,
        AN_Adj: Int,
        AN_CONSANGUINEOUS: String,
        AN_EAS: Int,
        AN_FEMALE: String,
        AN_FIN: Int,
        AN_MALE: String,
        AN_NFE: Int,
        AN_OTH: Int,
        AN_POPMAX: Array[String],
        AN_SAS: Int,
        BaseQRankSum: Double,
        CCC: Int,
        CSQ: Array[String],
        ClippingRankSum: Double,
        DB: Boolean,
        DOUBLETON_DIST: Array[String],
        DP: Int,
        DP_HIST: Array[String],
        DS: Boolean,
        END: Int,
        ESP_AC: Array[String],
        ESP_AF_GLOBAL: Array[String],
        ESP_AF_POPMAX: Array[String],
        FS: Double,
        GQ_HIST: Array[String],
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
        Hom_CONSANGUINEOUS: Array[String],
        Hom_EAS: Array[Int],
        Hom_FIN: Array[Int],
        Hom_NFE: Array[Int],
        Hom_OTH: Array[Int],
        Hom_SAS: Array[Int],
        InbreedingCoeff: Double,
        K1_RUN: Array[String],
        K2_RUN: Array[String],
        K3_RUN: Array[String],
        KG_AC: Array[String],
        KG_AF_GLOBAL: Array[String],
        KG_AF_POPMAX: Array[String],
        MLEAC: Array[Int],
        MLEAF: Array[Double],
        MQ: Double,
        MQ0: Int,
        MQRankSum: Double,
        NCC: Int,
        NEGATIVE_TRAIN_SITE: Boolean,
        OriginalContig: String,
        OriginalStart: String,
        POPMAX: Array[String],
        POSITIVE_TRAIN_SITE: Boolean,
        QD: Double,
        ReadPosRankSum: Double,
        VQSLOD: Double,
        clinvar_conflicted: Array[String],
        clinvar_measureset_id: Array[String],
        clinvar_mut: Array[String],
        clinvar_pathogenic: Array[String],
        culprit: String
    }
}
"""