from collections.abc import Callable
from enum import StrEnum

import hail as hl

from loading_pipeline.lib.annotations import gcnv, mito, shared, snv_indel, sv
from loading_pipeline.lib.core.definitions import ReferenceGenome, SampleType
from loading_pipeline.lib.core.environment import Env


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

    def entries_table_key_expression(
        self,
        ht: hl.Table,
        sample_type: SampleType,
    ) -> dict[str, hl.Expression]:
        if self in {DatasetType.GCNV, DatasetType.SV}:
            return {'sign': 1, 'variantId': ht.variant_id}
        return {
            'sample_type': sample_type.value,
            'sign': 1,
            'variantId': shared.variant_id(ht),
            'xpos': shared.xpos(ht),
        }

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
                'info.SEQR_INTERNAL_TRUTH_VID': hl.tstr,
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
    def has_multi_allelic_variants(self) -> bool:
        return self == DatasetType.SNV_INDEL

    @property
    def family_entries_filter_fn(self) -> Callable[[hl.StructExpression], bool]:
        return {
            DatasetType.GCNV: lambda e: hl.is_defined(e.gt),
        }.get(self, lambda e: e.gt > 0)

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
    ) -> dict[str, Callable[..., hl.Expression]]:
        GRCh37_fns = {  # noqa: N806
            DatasetType.SNV_INDEL: {
                'rsid': shared.rsid,
                'CAID': lambda *_, **__: hl.missing(hl.tstr),
                'variantId': shared.variant_id,
                'sortedTranscriptConsequences': snv_indel.subsetted_sorted_transcript_consequences_grch37,
                'transcripts': shared.sorted_transcript_consequences,
                'liftedOverChrom': shared.lifted_over_chrom,
                'liftedOverPos': shared.lifted_over_pos,
            },
            DatasetType.MITO: {
                'commonLowHeteroplasmy': mito.common_low_heteroplasmy,
                'haplogroupDefining': mito.haplogroupDefining,
                'mitotip': mito.mitotip,
                'rsid': mito.rsid,
                'variantId': shared.variant_id,
                'sortedTranscriptConsequences': shared.sorted_transcript_consequences,
                'liftedOverPos': shared.lifted_over_pos,
            },
            DatasetType.SV: {
                'algorithms': sv.algorithms,
                'bothsidesSupport': sv.bothsides_support,
                'chrom': sv.chrom,
                'cpxIntervals': sv.cpx_intervals,
                'end': sv.end,
                'pos': sv.pos,
                'populations': sv.populations,
                'predictions': sv.predictions,
                'sortedGeneConsequences': sv.sorted_gene_consequences,
                'svType': sv.sv_type,
                'svTypeDetail': sv.sv_type_detail,
                'variantId': sv.variant_id,
                'xpos': shared.xpos,
                'endChrom': sv.end_chrom,
                'svSourceDetail': sv.sv_source_detail,
                'liftedOverChrom': shared.lifted_over_chrom,
                'liftedOverPos': shared.lifted_over_pos,
                'rg37LocusEnd': shared.lifted_over_locus_end,
            },
            DatasetType.GCNV: {
                'chrom': gcnv.chrom,
                'end': gcnv.end,
                'numExon': gcnv.num_exon,
                'pos': gcnv.pos,
                'populations': gcnv.populations,
                'predictions': gcnv.predictions,
                'sortedGeneConsequences': gcnv.sorted_gene_consequences,
                'svType': gcnv.sv_type,
                'variantId': gcnv.variant_id,
                'xpos': gcnv.xpos,
                'liftedOverChrom': shared.lifted_over_chrom,
                'liftedOverPos': shared.lifted_over_pos,
                'rg37LocusEnd': shared.lifted_over_locus_end,
            },
        }
        if reference_genome == ReferenceGenome.GRCh37:
            return GRCh37_fns[self]
        return {
            DatasetType.SNV_INDEL: {
                **GRCh37_fns[DatasetType.SNV_INDEL],
                'sortedTranscriptConsequences': snv_indel.subsetted_sorted_transcript_consequences,
                'transcripts': snv_indel.sorted_transcript_consequences,
                'sortedRegulatoryFeatureConsequences': snv_indel.subsetted_sorted_regulatory_feature_consequences,
                'sortedRegulatoryFeatureConsequences_detail': snv_indel.sorted_regulatory_feature_consequences,
                'sortedMotifFeatureConsequences': snv_indel.subsetted_sorted_motif_feature_consequences,
                'sortedMotifFeatureConsequences_detail': snv_indel.sorted_motif_feature_consequences,
            },
            DatasetType.MITO: {
                **GRCh37_fns[DatasetType.MITO],
            },
            DatasetType.SV: {
                **GRCh37_fns[DatasetType.SV],
            },
            DatasetType.GCNV: {
                **GRCh37_fns[DatasetType.GCNV],
            },
        }[self]

    def variants_export_field_names(
        self,
        reference_genome: ReferenceGenome,
    ) -> list[str]:
        annotations = self.formatting_annotation_fns(reference_genome).keys()
        detail_fields = self.variant_details_export_fields(reference_genome).values()
        return sorted(set(annotations) - set(detail_fields))

    def variant_details_export_fields(
        self,
        reference_genome: ReferenceGenome,
    ) -> dict[str, str]:
        fields = {
            DatasetType.SNV_INDEL: {
                field: field
                for field in [
                    'key_',
                    'variantId',
                    'rsid',
                    'CAID',
                    'liftedOverChrom',
                    'liftedOverPos',
                ]
            },
        }
        if reference_genome == ReferenceGenome.GRCh38:
            fields[DatasetType.SNV_INDEL].update(
                {
                    'sortedMotifFeatureConsequences': 'sortedMotifFeatureConsequences_detail',
                    'sortedRegulatoryFeatureConsequences': 'sortedRegulatoryFeatureConsequences_detail',
                },
            )
        fields[DatasetType.SNV_INDEL]['transcripts'] = 'transcripts'
        return fields.get(self, {})

    def liftover_annotation_fns(
        self,
        reference_genome: ReferenceGenome,
    ) -> dict[str, Callable[..., hl.Expression]]:
        if reference_genome == ReferenceGenome.GRCh37:
            return {
                DatasetType.SNV_INDEL: {'lifted_over_locus': snv_indel.rg38_locus},
            }.get(self, {})
        return {
            DatasetType.SNV_INDEL: {'lifted_over_locus': shared.rg37_locus},
            DatasetType.MITO: {'lifted_over_locus': shared.rg37_locus},
            DatasetType.SV: {
                'lifted_over_locus': shared.rg37_locus,
                'lifted_over_locus_end': sv.rg37_locus_end,
            },
            DatasetType.GCNV: {
                'lifted_over_locus': gcnv.rg37_locus,
                'lifted_over_locus_end': gcnv.rg37_locus_end,
            },
        }[self]

    @property
    def genotype_entry_annotation_fns(self) -> dict[str, Callable[..., hl.Expression]]:
        return {
            DatasetType.SNV_INDEL: {
                'gt': shared.gt,
                'gq': shared.GQ,
                'ab': snv_indel.AB,
                'dp': snv_indel.DP,
            },
            DatasetType.MITO: {
                'gt': shared.gt,
                'dp': mito.DP,
                'hl': mito.HL,
                'mitoCn': mito.mito_cn,
                'contamination': mito.contamination,
            },
            DatasetType.SV: {
                'gt': shared.gt,
                'cn': sv.CN,
                'gq': shared.GQ,
                'newCall': sv.new_call,
                'prevCall': sv.prev_call,
                'prevNumAlt': sv.prev_num_alt,
            },
            DatasetType.GCNV: {
                'gt': gcnv.gt,
                'cn': gcnv.CN,
                'qs': gcnv.QS,
                'defragged': gcnv.defragged,
                'start': gcnv.start,
                'end': gcnv.sample_end,
                'numExon': gcnv.sample_num_exon,
                'geneIds': gcnv.gene_ids,
                'newCall': gcnv.new_call,
                'prevCall': gcnv.prev_call,
                'prevOverlap': gcnv.prev_overlap,
            },
        }[self]

    @property
    def filter_invalid_sites(self):
        return self == DatasetType.SNV_INDEL

    @property
    def should_write_new_variant_details(self):
        return self == DatasetType.SNV_INDEL

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
