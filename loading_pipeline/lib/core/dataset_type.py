from collections.abc import Callable
from enum import StrEnum

import hail as hl

from loading_pipeline.lib.annotations import gcnv, mito, shared, snv_indel, sv
from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.core.environment import Env

MITO_MIN_HOM_THRESHOLD = 0.95
ZERO = 0.0


class DatasetType(StrEnum):
    GCNV = 'GCNV'
    MITO = 'MITO'
    SNV_INDEL = 'SNV_INDEL'
    SV = 'SV'

    @property
    def reference_genomes(self) -> list[ReferenceGenome]:
        return {
            DatasetType.SNV_INDEL: [ReferenceGenome.GRCh37, ReferenceGenome.GRCh38],
            DatasetType.MITO: [ReferenceGenome.GRCh38],
            DatasetType.GCNV: [ReferenceGenome.GRCh38],
            DatasetType.SV: [ReferenceGenome.GRCh38],
        }[self]

    def table_key_type(
        self,
        reference_genome: ReferenceGenome,
    ) -> hl.tstruct:
        default_key = hl.tstruct(
            locus=hl.tlocus(reference_genome.value),
            alleles=hl.tarray(hl.tstr),
        )
        return {
            DatasetType.GCNV: hl.tstruct(variant_id=hl.tstr),
            DatasetType.SV: hl.tstruct(variant_id=hl.tstr),
        }.get(self, default_key)

    def table_key_format_fn(
        self,
        reference_genome: ReferenceGenome,
    ) -> Callable[[hl.StructExpression], str]:
        if self in {DatasetType.GCNV, DatasetType.SV}:
            return lambda s: s.variant_id
        return (
            lambda s: f'{s.locus.contig if reference_genome == ReferenceGenome.GRCh37 else s.locus.contig.replace("chr", "")}-{s.locus.position}-{"-".join(s.alleles)}'
        )

    @property
    def col_fields(
        self,
    ) -> list[str]:
        return {
            DatasetType.SNV_INDEL: {},
            DatasetType.MITO: {
                'contamination': {hl.tstr, hl.tfloat64},
                'mito_cn': hl.tfloat64,
            },
            DatasetType.SV: {},
            DatasetType.GCNV: {},
        }[self]

    @property
    def entries_fields(
        self,
    ) -> list[str]:
        return {
            DatasetType.SNV_INDEL: {
                'GT': hl.tcall,
                'AD': hl.tarray(hl.tint32),
                'GQ': hl.tint32,
            },
            DatasetType.MITO: {
                'GT': hl.tcall,
                'DP': hl.tint32,
                'MQ': {hl.tfloat64, hl.tint32},
                'HL': hl.tfloat64,
            },
            DatasetType.SV: {
                'GT': hl.tcall,
                'CONC_ST': hl.tarray(hl.tstr),
                'GQ': hl.tint32,
                'RD_CN': hl.tint32,
            },
            DatasetType.GCNV: {
                'any_ovl': hl.tstr,
                'defragmented': hl.tbool,
                'genes_any_overlap_Ensemble_ID': hl.tstr,
                'genes_any_overlap_totalExons': hl.tint32,
                'identical_ovl': hl.tstr,
                'is_latest': hl.tbool,
                'no_ovl': hl.tbool,
                'sample_start': hl.tint32,
                'sample_end': hl.tint32,
                'CN': hl.tint32,
                'GT': hl.tstr,
                'QS': hl.tint32,
            },
        }[self]

    @property
    def row_fields(
        self,
    ) -> list[str]:
        return {
            DatasetType.SNV_INDEL: {
                'rsid': hl.tstr,
                'filters': hl.tset(hl.tstr),
            },
            DatasetType.MITO: {
                'rsid': hl.tset(hl.tstr),
                'filters': hl.tset(hl.tstr),
                'common_low_heteroplasmy': hl.tbool,
                'hap_defining_variant': hl.tbool,
                'mitotip_trna_prediction': hl.tstr,
                'vep': hl.tstruct,
            },
            DatasetType.SV: {
                'locus': hl.tlocus(ReferenceGenome.GRCh38.value),
                'alleles': hl.tarray(hl.tstr),
                'filters': hl.tset(hl.tstr),
                'info.AC': hl.tarray(hl.tint32),
                'info.AF': hl.tarray(hl.tfloat64),
                'info.ALGORITHMS': hl.tarray(hl.tstr),
                'info.BOTHSIDES_SUPPORT': hl.tbool,
                'info.AN': hl.tint32,
                'info.CHR2': hl.tstr,
                'info.CPX_INTERVALS': hl.tarray(hl.tstr),
                'info.CPX_TYPE': hl.tstr,
                'info.END': hl.tint32,
                'info.END2': hl.tint32,
                'info.N_HET': hl.tint32,
                'info.N_HOMALT': hl.tint32,
                'info.GNOMAD_V4.1_TRUTH_VID': hl.tstr,
                'info.StrVCTVRE': hl.tstr,
                'info.SVLEN': hl.tint32,
                **sv.CONSEQ_PREDICTED_GENE_COLS,
            },
            DatasetType.GCNV: {
                'cg_genes': hl.tset(hl.tstr),
                'chr': hl.tstr,
                'end': hl.tint32,
                'filters': hl.tset(hl.tstr),
                'gene_ids': hl.tset(hl.tstr),
                'lof_genes': hl.tset(hl.tstr),
                'num_exon': hl.tint32,
                'sc': hl.tint32,
                'sf': hl.tfloat64,
                'start': hl.tint32,
                'strvctvre_score': hl.tstr,
                'svtype': hl.tstr,
            },
        }[self]

    @property
    def excluded_filters(self) -> hl.SetExpression:
        return {
            DatasetType.SNV_INDEL: hl.empty_set(hl.tstr),
            DatasetType.MITO: hl.set(['PASS']),
            DatasetType.SV: hl.set(['PASS', 'BOTHSIDES_SUPPORT']),
            DatasetType.GCNV: hl.empty_set(hl.tstr),
        }[self]

    @property
    def invalid_allele_types(self) -> hl.SetExpression:
        return {
            DatasetType.SV: hl.set([hl.genetics.allele_type.AlleleType.UNKNOWN]),
        }.get(
            self,
            hl.set(
                [
                    hl.genetics.allele_type.AlleleType.UNKNOWN,
                    hl.genetics.allele_type.AlleleType.SYMBOLIC,
                ],
            ),
        )

    def has_gencode_ensembl_to_refseq_id_mapping(
        self,
        reference_genome: ReferenceGenome,
    ) -> bool:
        return (
            self == DatasetType.SNV_INDEL and reference_genome == ReferenceGenome.GRCh38
        )

    def expect_tdr_metrics(
        self,
        reference_genome: ReferenceGenome,
    ) -> bool:
        return (
            self == DatasetType.SNV_INDEL and reference_genome == ReferenceGenome.GRCh38
        )

    @property
    def has_gencode_gene_symbol_to_gene_id_mapping(self) -> bool:
        return self == DatasetType.SV

    @property
    def has_multi_allelic_variants(self) -> bool:
        return self == DatasetType.SNV_INDEL

    @property
    def family_entries_filter_fn(self) -> Callable[[hl.StructExpression], bool]:
        return {
            DatasetType.GCNV: lambda e: hl.is_defined(e.GT),
        }.get(self, lambda e: e.GT.is_non_ref())

    @property
    def can_run_validation(self) -> bool:
        return self == DatasetType.SNV_INDEL

    @property
    def check_sex_and_relatedness(self) -> bool:
        return self == DatasetType.SNV_INDEL

    @property
    def veppable(self) -> bool:
        return self == DatasetType.SNV_INDEL

    def formatting_annotation_fns(
        self,
        reference_genome: ReferenceGenome,
    ) -> list[Callable[..., hl.Expression]]:
        GRCh37_fns = {  # noqa: N806
            DatasetType.SNV_INDEL: [
                shared.rsid,
                shared.variant_id,
                shared.xpos,
                shared.sorted_transcript_consequences,
                snv_indel.rg38_locus,
            ],
            DatasetType.MITO: [
                mito.common_low_heteroplasmy,
                mito.haplogroup,
                mito.mitotip,
                mito.rsid,
                shared.variant_id,
                shared.xpos,
                shared.sorted_transcript_consequences,
            ],
            DatasetType.SV: [
                sv.algorithms,
                sv.bothsides_support,
                sv.cpx_intervals,
                sv.end_locus,
                sv.gnomad_svs,
                sv.sorted_gene_consequences,
                sv.start_locus,
                sv.strvctvre,
                sv.sv_type_id,
                sv.sv_type_detail_id,
                sv.sv_len,
                shared.xpos,
            ],
            DatasetType.GCNV: [
                gcnv.end_locus,
                gcnv.num_exon,
                gcnv.sorted_gene_consequences,
                gcnv.start_locus,
                gcnv.strvctvre,
                gcnv.sv_type_id,
                gcnv.xpos,
            ],
        }
        if reference_genome == ReferenceGenome.GRCh37:
            return GRCh37_fns[self]
        return {
            DatasetType.SNV_INDEL: [
                shared.rsid,
                shared.variant_id,
                shared.xpos,
                shared.rg37_locus,
                snv_indel.check_ref,
                snv_indel.sorted_transcript_consequences,
                snv_indel.sorted_regulatory_feature_consequences,
                snv_indel.sorted_motif_feature_consequences,
            ],
            DatasetType.MITO: [
                *GRCh37_fns[DatasetType.MITO],
                shared.rg37_locus,
            ],
            DatasetType.SV: [
                *GRCh37_fns[DatasetType.SV],
                shared.rg37_locus,
                sv.rg37_locus_end,
            ],
            DatasetType.GCNV: [
                *GRCh37_fns[DatasetType.GCNV],
                gcnv.rg37_locus,
                gcnv.rg37_locus_end,
            ],
        }[self]

    @property
    def genotype_entry_annotation_fns(self) -> list[Callable[..., hl.Expression]]:
        return {
            DatasetType.SNV_INDEL: [
                shared.GQ,
                snv_indel.AB,
                snv_indel.DP,
                shared.GT,
            ],
            DatasetType.MITO: [
                mito.contamination,
                mito.DP,
                mito.HL,
                mito.mito_cn,
                mito.GQ,
                shared.GT,
            ],
            DatasetType.SV: [
                sv.CN,
                sv.concordance,
                shared.GQ,
                shared.GT,
            ],
            DatasetType.GCNV: [
                gcnv.concordance,
                gcnv.defragged,
                gcnv.sample_end,
                gcnv.sample_gene_ids,
                gcnv.sample_num_exon,
                gcnv.sample_start,
                gcnv.CN,
                gcnv.GT,
                gcnv.QS,
            ],
        }[self]

    @property
    def variant_frequency_annotation_fns(self) -> list[Callable[..., hl.Expression]]:
        return {
            DatasetType.GCNV: [
                gcnv.gt_stats,
            ],
        }.get(self, [])

    @property
    def filter_invalid_sites(self):
        return self == DatasetType.SNV_INDEL

    @property
    def should_export_to_vcf(self):
        return self == DatasetType.SV

    @property
    def export_vcf_annotation_fns(self) -> list[Callable[..., hl.Expression]]:
        return {
            DatasetType.SV: [
                sv.locus,
                sv.alleles,
                sv.info,
            ],
        }[self]

    @property
    def should_write_new_variant_details(self):
        return self == DatasetType.SNV_INDEL

    @property
    def overwrite_male_non_par_calls(self) -> None:
        return self == DatasetType.SV

    @property
    def re_key_by_seqr_internal_truth_vid(self) -> None:
        return self == DatasetType.SV

    @property
    def dataproc_primary_workers(self) -> int:
        if self == DatasetType.SNV_INDEL:
            return Env.GCLOUD_DATAPROC_PRIMARY_WORKERS
        return 1

    @property
    def dataproc_preemptibles(self) -> int | None:
        if self == DatasetType.SNV_INDEL:
            return Env.GCLOUD_DATAPROC_SECONDARY_WORKERS
        return 1
