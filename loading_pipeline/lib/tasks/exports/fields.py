import hail as hl

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.tasks.exports.misc import reformat_transcripts_for_export

FIVE_PERCENT = 0.05
STANDARD_CONTIGS = hl.set(
    [c.replace('MT', 'M') for c in ReferenceGenome.GRCh37.standard_contigs],
)


def reference_independent_contig(locus: hl.LocusExpression):
    contig = locus.contig.replace('^chr', '').replace('MT', 'M')
    return hl.or_missing(
        # lifted over alternate contigs may be present
        # even though the primary contig is filtered to
        # standard contigs earlier in the pipeline
        STANDARD_CONTIGS.contains(contig),
        contig,
    )


def get_dataset_type_specific_variants_annotations(
    ht: hl.Table,
    dataset_type: DatasetType,
):
    return {
        DatasetType.MITO: lambda ht: {
            'commonLowHeteroplasmy': ht.common_low_heteroplasmy,
            'haplogroupDefining': ht.haplogroup.is_defining,
            'mitotip': ht.mitotip.trna_prediction,
        },
        DatasetType.SV: lambda ht: {
            'algorithms': ht.algorithms,
            'bothsidesSupport': ht.bothsides_support,
            'cpxIntervals': ht.cpxIntervals.map(
                lambda cpx_i: hl.Struct(
                    chrom=reference_independent_contig(cpx_i.start),
                    start=cpx_i.start.position,
                    end=cpx_i.end.position,
                    type=cpx_i.type,
                ),
            ),
            'endChrom': hl.or_missing(
                (
                    (ht.sv_type != 'INS')
                    & (ht.start_locus.contig != ht.end_locus.contig)
                ),
                reference_independent_contig(ht.end_locus),
            ),
            'svSourceDetail': hl.or_missing(
                (
                    (ht.sv_type == 'INS')
                    & (ht.start_locus.contig != ht.end_locus.contig)
                ),
                hl.Struct(chrom=reference_independent_contig(ht.end_locus)),
            ),
            'svType': ht.sv_type,
            'svTypeDetail': ht.sv_type_detail,
            'predictions': hl.Struct(
                strvctvre=ht.strvctvre.score,
            ),
            'populations': hl.Struct(
                gnomad_svs=hl.Struct(
                    af=ht.gnomad_svs.AF,
                    het=ht.gnomad_svs.N_HET,
                    hom=ht.gnomad_svs.N_HOM,
                    id=ht.gnomad_svs.ID,
                ),
            ),
        },
        DatasetType.GCNV: lambda ht: {
            'numExon': ht.num_exon,
            'svType': ht.sv_type,
            'predictions': hl.Struct(
                strvctvre=ht.strvctvre.score,
            ),
            'populations': hl.Struct(
                sv_callset=hl.Struct(
                    ac=ht.gt_stats.AC,
                    af=ht.gt_stats.AF,
                    an=ht.gt_stats.AN,
                    het=ht.gt_stats.Het,
                    hom=ht.gt_stats.Hom,
                ),
            ),
        },
    }[dataset_type](ht)


def get_calls_export_fields(
    ht: hl.Table,
    fe: hl.Struct,
    dataset_type: DatasetType,
):
    return {
        DatasetType.SNV_INDEL: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            gq=fe.GQ,
            ab=fe.AB,
            dp=fe.DP,
        ),
        DatasetType.MITO: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            dp=fe.DP,
            hl=fe.HL,
            mitoCn=fe.mito_cn,
            contamination=fe.contamination,
        ),
        DatasetType.SV: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            cn=fe.CN,
            gq=fe.GQ,
            newCall=fe.concordance.new_call,
            prevCall=fe.concordance.prev_call,
            prevNumAlt=fe.concordance.prev_num_alt,
        ),
        DatasetType.GCNV: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            cn=fe.CN,
            qs=fe.QS,
            defragged=fe.defragged,
            start=hl.or_else(fe.sample_start, ht.start_locus.position),
            end=hl.or_else(fe.sample_end, ht.end_locus.position),
            numExon=hl.or_else(fe.sample_num_exon, ht.num_exon),
            geneIds=hl.or_else(
                fe.sample_gene_ids,
                hl.set(ht.sorted_gene_consequences.gene_id),
            ),
            newCall=fe.concordance.new_call,
            prevCall=fe.concordance.prev_call,
            prevOverlap=fe.concordance.prev_overlap,
        ),
    }[dataset_type](fe)


def get_entries_export_fields(
    ht: hl.Table,
    dataset_type: DatasetType,
    sample_type: SampleType,
    project_guid: str,
):
    return {
        'key_': ht.key_,
        'project_guid': project_guid,
        'family_guid': ht.family_entries.family_guid[0],
        **(
            {
                'sample_type': sample_type.value,
            }
            if dataset_type in {DatasetType.SNV_INDEL, DatasetType.MITO}
            else {}
        ),
        'xpos': ht.xpos,
        **(
            {
                'geneIds': hl.set(ht.sorted_gene_consequences.gene_id)
                if dataset_type == DatasetType.SV
                else hl.set(ht.sorted_transcript_consequences.gene_id)
                if dataset_type == DatasetType.SNV_INDEL
                else None,
            }
            if dataset_type in {DatasetType.SV, DatasetType.SNV_INDEL}
            else {}
        ),
        'filters': ht.filters,
        'calls': hl.sorted(ht.family_entries, key=lambda fe: fe.s).map(
            lambda fe: get_calls_export_fields(ht, fe, dataset_type),
        ),
        'sign': 1,
    }


def get_variant_id_fields(
    ht: hl.Table,
    dataset_type: DatasetType,
):
    return {
        DatasetType.SNV_INDEL: lambda ht: {
            'variantId': ht.variant_id,
            'rsid': ht.rsid,
            'CAID': hl.missing(hl.tstr),
        },
        DatasetType.MITO: lambda ht: {
            'variantId': ht.variant_id,
            'rsid': ht.rsid,
        },
        DatasetType.SV: lambda ht: {
            'variantId': ht.variant_id,
        },
        DatasetType.GCNV: lambda ht: {
            'variantId': ht.variant_id,
        },
    }[dataset_type](ht)


def get_lifted_over_position_fields(ht: hl.Table, dataset_type: DatasetType):
    if dataset_type == DatasetType.MITO:
        return {'liftedOverPos': ht.rg37_locus.position}
    return {
        'liftedOverChrom': (
            reference_independent_contig(ht.rg37_locus)
            if hasattr(ht, 'rg37_locus')
            else reference_independent_contig(ht.rg38_locus)
        ),
        'liftedOverPos': (
            hl.or_missing(
                hl.is_defined(reference_independent_contig(ht.rg37_locus)),
                ht.rg37_locus.position,
            )
            if hasattr(ht, 'rg37_locus')
            else ht.rg38_locus.position
        ),
    }


def get_consequences_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
):
    return {
        DatasetType.SNV_INDEL: lambda ht: {
            **(
                {
                    'sortedMotifFeatureConsequences': ht.sortedMotifFeatureConsequences,
                    'sortedRegulatoryFeatureConsequences': ht.sortedRegulatoryFeatureConsequences,
                }
                if reference_genome == ReferenceGenome.GRCh38
                else {}
            ),
            'sortedTranscriptConsequences': ht.sortedTranscriptConsequences,
        },
        DatasetType.MITO: lambda ht: {
            # MITO transcripts are not exported to their own table,
            # but the structure should be preserved here.
            'sortedTranscriptConsequences': hl.enumerate(
                ht.sortedTranscriptConsequences,
            ).starmap(reformat_transcripts_for_export),
        },
        DatasetType.SV: lambda ht: {
            'sortedGeneConsequences': ht.sortedGeneConsequences,
        },
        DatasetType.GCNV: lambda ht: {
            'sortedGeneConsequences': ht.sortedGeneConsequences,
        },
    }[dataset_type](ht)


def get_variants_export_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
):
    if dataset_type in {DatasetType.SV, DatasetType.GCNV}:
        rg37_contig = reference_independent_contig(ht.rg37_locus_end)
        position_fields = {
            'chrom': reference_independent_contig(ht.start_locus),
            'pos': ht.start_locus.position,
            'end': ht.end_locus.position,
            'rg37LocusEnd': hl.Struct(
                contig=rg37_contig,
                position=hl.or_missing(
                    hl.is_defined(rg37_contig),
                    ht.rg37_locus_end.position,
                ),
            ),
        }
        return {
            'key_': ht.key_,
            'xpos': ht.xpos,
            **position_fields,
            **get_variant_id_fields(ht, dataset_type),
            **get_lifted_over_position_fields(ht, dataset_type),
            **get_dataset_type_specific_variants_annotations(ht, dataset_type),
            **get_consequences_fields(ht, reference_genome, dataset_type),
        }
    if dataset_type == DatasetType.MITO:
        return {
            'key_': ht.key_,
            **get_variant_id_fields(ht, dataset_type),
            **get_lifted_over_position_fields(ht, dataset_type),
            **get_dataset_type_specific_variants_annotations(ht, dataset_type),
            **get_consequences_fields(ht, reference_genome, dataset_type),
        }
    return {
        'key_': ht.key_,
        **get_consequences_fields(ht, reference_genome, dataset_type),
    }


def get_variant_details_export_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
):
    return {
        'key_': ht.key_,
        **get_variant_id_fields(ht, dataset_type),
        **get_lifted_over_position_fields(ht, dataset_type),
        **(
            {
                'sortedMotifFeatureConsequences': ht.sortedMotifFeatureConsequences,
                'sortedRegulatoryFeatureConsequences': ht.sortedRegulatoryFeatureConsequences,
            }
            if reference_genome == ReferenceGenome.GRCh38
            else {}
        ),
        'transcripts': hl.enumerate(
            ht.sortedTranscriptConsequences,
        ).starmap(reformat_transcripts_for_export),
    }
