import argparse
import hail
import os
import sys

from seqr.pipelines.hail.utils import get_gnomad_exomes_vds, get_gnomad_genomes_vds, get_cadd_vds
from seqr.pipelines.hail.utils.get_1kg_phase3_vds import get_g1k_phase3_vds
from seqr.pipelines.hail.utils.get_clinvar_vds import get_clinvar_vds
from seqr.pipelines.hail.utils.get_exac_vds import get_exac_vds
from seqr.pipelines.hail.utils.get_mpc_vds import get_mpc_vds

hc = hail.HailContext()

# exac, gnomad, 1kg, clinvar, cadd

p = argparse.ArgumentParser()
p.add_argument("-g", "--genome_version", help="Genome build: 37 or 38", choices=["37", "38"], required=True )
#p.add_argument("-k", "--cassandra-keyspace", help="Cassandra keyspace", required=True)
#p.add_argument("-t", "--cassandra-table", help="Cassandra table", required=True)
#p.add_argument("--export-ref", action="store_true")
p.add_argument("dataset_id", help="variant dataset id")
p.add_argument("input_path", help="input VCF or VDS")
args = p.parse_args()

genome_version = args.genome_version

dataset_id = args.dataset_id   #or os.path.basename(input_path).replace(".vds", "").replace(".vcf.gz", "").replace(".vcf.bgz", "")
input_path = args.input_path

print("Input path: %s" % input_path)

# https://github.com/hail-is/hail/pull/1779

if input_path.endswith(".vds"):
    vds = hc.read(input_path)
else:
    vds = hc.import_vcf(input_path, min_partitions=1000, force_bgz=True)

g1k_vds = get_g1k_phase3_vds(hc, genome_version)
exac_vds = get_exac_vds(hc, genome_version)
gnomad_exomes_vds = get_gnomad_exomes_vds(hc, genome_version)
gnomad_genomes_vds = get_gnomad_genomes_vds(hc, genome_version)
clinvar_vds = get_clinvar_vds(hc, genome_version)
mpc_vds = get_mpc_vds(hc, genome_version)
cadd_vds = get_cadd_vds(hc, genome_version)

vds = vds.sample_qc().variant_qc()
vds = vds.impute_sex(maf_threshold=0.05)
vds = (
    vds
       .annotate_variants_vds(g1k_vds, expr="va.g1k = vds.for_seqr")
       .annotate_variants_vds(exac_vds, expr="va.exac = vds.for_seqr")
       .annotate_variants_vds(gnomad_exomes_vds, expr="va.gnomad_exomes = vds.for_seqr")
       .annotate_variants_vds(gnomad_genomes_vds, expr="va.gnomad_genomes = vds.for_seqr")
       .annotate_variants_expr("""va.vep.sorted_transcript_consequences = va.vep.transcript_consequences.map(
            c => select(c,
                amino_acids,
                biotype,
                canonical,
                cdna_start,
                cdna_end,
                codons,
                consequence_terms,
                distance,
                domains,
                exon,
                gene_id,
                transcript_id,
                protein_id,
                gene_symbol,
                gene_symbol_source,
                hgnc_id,
                hgvsc,
                hgvsp,
                lof,
                lof_flags,
                lof_filter,
                lof_info)
            ).sortBy(c => let
                is_coding=(c.biotype=="protein_coding") and
                is_most_severe=c.consequence_terms.toSet.contains(va.vep.most_severe_consequence) and
                is_canonical=(c.canonical==1) in

                if(is_coding)
                    if(is_most_severe)
                        if(is_canonical)  1  else  2
                    else  3
                else
                    if(is_most_severe)
                        if(is_canonical)  4  else  5
                    else  6
            )
        """)
       )


print(vds.variant_schema)

    #.annotate_variants_vds(root="va.dbnsfp", other="%(data_dir)s/dbnsfp/dbNSFP_3.2a_variant.filtered.allhg19_nodup.vds" % locals())
    #.annotations_variants_table(root="va.revel", path="$(data_dir)s/revel/revel_all_chromosomes.tsv.bgz", variant_expr="Variant(_0, _1.toInt, _2, _3)", code="revel_score=_4.toFloat", header=False)


kt = vds.variants_table()
p = kt.aggregate_by_key("consequence = va.info.CSQ.most_severe_consequence", "variant_count = v.count()").to_pandas()
p.sort("variant_count")
kt.aggregate_by_key("contig = v.contig", "variant_count = v.count()").to_pandas()
kt.aggregate_by_key(
    "lof = va.info.CSQ.transcript_consequences.map(t => t.lof ).toSet.toArray.mkString(\",\")",
    "variant_count = v.count()"
).to_pandas()

kt.aggregate_by_key(
    "lof_filter = va.info.CSQ.transcript_consequences.map(t => t.lof_filter ).toSet.toArray.mkString(\",\")",
    "variant_count = v.count()"
).to_pandas()


"""
       .annotate_variants_expr()
       .export_variants_cass(variant_condition=""
            dataset_id="%(dataset_id)s",
            chrom=v.contig,
            start=v.start,
            end=v.start + v.ref.length - 1,
            ref=v.ref,
            alt=v.alt,
            filters = va.filters,
            pass = va.pass,
            rsid = va.rsid,
            AC = va.info.AC[va.aIndex-1],
            AN = va.info.AN,
            AF = va.info.AF[va.aIndex-1],
            was_split = va.wasSplit,
            clinvar_clinsig = va.clinvar.clinical_significance,
            clinvar_review_status = va.clinvar.review_status,
            clinvar_inheritance_mode = va.clinvar.inheritance_modes.split(";").toSet,
            clinvar_disease_mechanism = va.clinvar.disease_mechanism.split(";").toSet,
            clinvar_gold_stars = va.clinvar.gold_stars,
            clinvar_is_pathogenic = va.clinvar.pathogenic,
            clinvar_is_conflicted = va.clinvar.conflicted,

            vep_gene_id = va.vep.transcript_consequences.map( x => x.gene_id ).toSet,
            vep_transcript_id = va.vep.transcript_consequences.map( x => x.transcript_id ).toSet,
            vep_most_severe_consequence = va.vep.most_severe_consequence,

            g1k_wgs_phase3_afr_af = va.g1k.info.AFR_AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_amr_af = va.g1k.info.AMR_AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_eur_af = va.g1k.info.EUR_AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_eas_af = va.g1k.info.EAS_AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_sas_af = va.g1k.info.SAS_AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_global_af = va.g1k.info.AF[va.g1k.aIndex-1],
            g1k_wgs_phase3_popmax_af = va.g1k.info.POPMAX_AF,
            g1k_wgs_phase3_popmax = va.g1k.info.POPMAX,
            exac_v1_afr_af = if(va.exac.info.AN_AFR == 0) NA:Double else va.exac.info.AC_AFR[va.exac.aIndex-1]/va.exac.info.AN_AFR,
            exac_v1_amr_af = if(va.exac.info.AN_AMR == 0) NA:Double else va.exac.info.AC_AMR[va.exac.aIndex-1]/va.exac.info.AN_AMR,
            exac_v1_nfe_af = if(va.exac.info.AN_NFE == 0) NA:Double else va.exac.info.AC_NFE[va.exac.aIndex-1]/va.exac.info.AN_NFE,
            exac_v1_fin_af = if(va.exac.info.AN_FIN == 0) NA:Double else va.exac.info.AC_FIN[va.exac.aIndex-1]/va.exac.info.AN_FIN,
            exac_v1_eas_af = if(va.exac.info.AN_EAS == 0) NA:Double else va.exac.info.AC_EAS[va.exac.aIndex-1]/va.exac.info.AN_EAS,
            exac_v1_sas_af = if(va.exac.info.AN_SAS == 0) NA:Double else va.exac.info.AC_SAS[va.exac.aIndex-1]/va.exac.info.AN_SAS,
            exac_v1_global_af = va.exac.info.AF[va.exac.aIndex-1],
            exac_v1_popmax_af = if(va.exac.info.AN_POPMAX[va.exac.aIndex-1] == 0) NA:Double else va.exac.info.AC_POPMAX[va.exac.aIndex-1]/va.exac.info.AN_POPMAX[va.exac.aIndex-1],
            exac_v1_popmax = va.exac.info.POPMAX[va.exac.aIndex-1],
            twinsuk_af = va.dbnsfp.TWINSUK_AF.toDouble,
            alspac_af = va.dbnsfp.ALSPAC_AF.toDouble,
            esp65000_aa_af = va.dbnsfp.ESP6500_AA_AF.toDouble,
            esp65000_ea_af = va.dbnsfp.ESP6500_EA_AF.toDouble,

            dbnsfp_sift_pred = va.dbnsfp.SIFT_pred,
            dbnsfp_polyphen2_hdiv_pred = va.dbnsfp.Polyphen2_HDIV_pred,
            dbnsfp_polyphen2_hvar_pred = va.dbnsfp.Polyphen2_HVAR_pred,
            dbnsfp_lrt_pred = va.dbnsfp.LRT_pred,
            dbnsfp_muttaster_pred = va.dbnsfp.MutationTaster_pred,
            dbnsfp_mutassesor_pred = va.dbnsfp.MutationAssessor_pred,
            dbnsfp_fathmm_pred = va.dbnsfp.FATHMM_pred,
            dbnsfp_provean_pred = va.dbnsfp.PROVEAN_pred,
            dbnsfp_metasvm_pred = va.dbnsfp.MetaSVM_pred,
            dbnsfp_metalr_pred = va.dbnsfp.MetaLR_pred,

            revel_score = va.revel.revel_score.toFloat,

            vep_annotations_sorted = json(va.vep.sorted_transcript_consequences),
            vep_consequences=va.vep.transcript_consequences.map( x => x.consequence_terms ).flatten().toSet,
            clinvar_submitter = va.clinvar.all_submitters.split(";").toSet,
            clinvar_trait = va.clinvar.all_traits.split(";").toSet,
            clinvar_pmid = va.clinvar.all_pmids.split(";").toSet,
            clinvar_age_of_onset = va.clinvar.age_of_onset.split(";").toSet,
            clinvar_prevalence = va.clinvar.prevalence.split(";").toSet,
            clinvar_origin = va.clinvar.origin.split(";").toSet,
            clinvar_xrefs = va.clinvar.xrefs
        "",
        genotype_condition=""
            num_alt = if(g.isCalled) g.nNonRefAlleles else -1,
            gq = if(g.isCalled) g.gq else NA:Int,
            ab = let s=g.ad.sum in if(g.isCalled && s != 0) (g.ad[0] / s).toFloat else NA:Float,
            dp = if(g.isCalled) g.dp else NA:Int,
            pl = if(g.isCalled) g.pl else NA:Array[Int]
        "",
         address="69.173.112.35",
         keyspace=cassandra_keyspace,
         table=cassandra_table,
         export_missing=False,
         export_ref=False)
       )
"""