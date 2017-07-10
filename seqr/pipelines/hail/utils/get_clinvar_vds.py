from pprint import pprint
from seqr.pipelines.hail.utils.run_annotation_utils import convert_info_fields_to_expr


def get_clinvar_vds(hail_context, genome_version):
    if genome_version == "37":
        clinvar_single_vcf = 'gs://seqr-reference-data/GRCh37/clinvar/clinvar_alleles.single.b37.vcf.gz'
        clinvar_multi_vcf = 'gs://seqr-reference-data/GRCh37/clinvar/clinvar_alleles.multi.b37.vcf.gz'
    elif genome_version == "38":
        clinvar_single_vcf = 'gs://seqr-reference-data/GRCh38/clinvar/clinvar_alleles.single.b38.vcf.gz'
        clinvar_multi_vcf = 'gs://seqr-reference-data/GRCh38/clinvar/clinvar_alleles.multi.b38.vcf.gz'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    clinvar_vds = (
        hail_context
            .import_vcf([clinvar_single_vcf, clinvar_multi_vcf], force_bgz=True, min_partitions=1000)
            .annotate_variants_expr(convert_info_fields_to_expr("""
                MEASURESET_TYPE: String,
                MEASURESET_ID: String,
                RCV: String,
                ALLELE_ID: String,
                CLINICAL_SIGNIFICANCE: String,
                PATHOGENIC: String,
                BENIGN: String,
                CONFLICTED: String,
                REVIEW_STATUS: String,
                GOLD_STARS: String,
                ALL_SUBMITTERS: String,
                ALL_TRAITS: String,
                ALL_PMIDS: String,
                INHERITANCE_MODES: String,
                AGE_OF_ONSET: String,
                PREVALENCE: String,
                DISEASE_MECHANISM: String,
                ORIGIN: String,
                XREFS: String
                """))
            .annotate_variants_expr("va = select(va, for_seqr)")
    )

    #pprint(clinvar_vds.variant_schema)

    return clinvar_vds
