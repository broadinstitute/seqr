from collections import OrderedDict

import hail as hl

from loading_pipeline.lib.annotations.enums import (
    BIOTYPES,
    FIVEUTR_CONSEQUENCES,
    LOF_FILTERS,
    MITOTIP_PATHOGENICITIES,
    MOTIF_CONSEQUENCE_TERMS,
    REGULATORY_BIOTYPES,
    REGULATORY_CONSEQUENCE_TERMS,
    SV_CONSEQUENCE_RANKS,
    SV_TYPE_DETAILS,
    SV_TYPES,
    TRANSCRIPT_CONSEQUENCE_TERMS,
)
from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.misc.nested_field import parse_nested_field


def snake_to_camelcase(snake_string: str):
    components = snake_string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camelcase_hl_struct(s: hl.StructExpression) -> hl.StructExpression:
    return s.rename({f: snake_to_camelcase(f) for f in s})


def sorted_hl_struct(s: hl.StructExpression) -> hl.StructExpression:
    if not isinstance(s, hl.StructExpression):
        return s
    return s.select(**{k: sorted_hl_struct(s[k]) for k in sorted(s)})


def array_structexpression_fields(ht: hl.Table):
    return [
        field
        for field in ht.row
        if isinstance(
            ht[field],
            hl.expr.expressions.typed_expressions.ArrayStructExpression,
        )
    ]


def reformat_transcripts_for_export(i: int, s: hl.StructExpression):
    formatted_s = (
        s.annotate(
            majorConsequence=s.consequenceTerms.first(),
            transcriptRank=i,
        )
        if hasattr(s, 'loftee')
        else s.annotate(
            loftee=hl.Struct(
                isLofNagnag=s.isLofNagnag,
                lofFilters=s.lofFilters,
            ),
            majorConsequence=s.consequenceTerms.first(),
            transcriptRank=i,
        ).drop('isLofNagnag', 'lofFilters')
    )
    return sorted_hl_struct(formatted_s)


def export_parquet_filterable_transcripts_fields(
    reference_genome: ReferenceGenome,
) -> OrderedDict[str, str]:
    fields = {
        k: k
        for k in [
            'canonical',
            'consequenceTerms',
            'geneId',
        ]
    }
    if reference_genome == ReferenceGenome.GRCh38:
        fields = {
            **fields,
            'alphamissensePathogenicity': 'alphamissense.pathogenicity',
            'extendedIntronicSpliceRegionVariant': 'spliceregion.extended_intronic_splice_region_variant',
            'fiveutrConsequence': 'utrannotator.fiveutrConsequence',
            'isManeSelect': 'isManeSelect',
        }
    # Parquet export expects all fields sorted alphabetically
    return OrderedDict(sorted(fields.items()))


def subset_consequences_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
) -> hl.Table:
    if reference_genome == ReferenceGenome.GRCh38:
        ht = ht.annotate(
            sortedMotifFeatureConsequences=ht.sortedMotifFeatureConsequences.map(
                lambda e: e.select(
                    'consequenceTerms',
                ),
            ),
            sortedRegulatoryFeatureConsequences=ht.sortedRegulatoryFeatureConsequences.map(
                lambda e: e.select(
                    'consequenceTerms',
                ),
            ),
            sortedTranscriptConsequences=ht.sortedTranscriptConsequences.map(
                lambda e: e.annotate(isManeSelect=hl.is_defined(e.maneSelect)),
            ),
        )
    return ht.annotate(
        sortedTranscriptConsequences=hl.enumerate(
            ht.sortedTranscriptConsequences,
        ).starmap(
            lambda idx, c: c.select(
                **{
                    new_field_name: parse_nested_field(
                        ht.sortedTranscriptConsequences,
                        existing_field_name,
                    )[idx]
                    for new_field_name, existing_field_name in export_parquet_filterable_transcripts_fields(
                        reference_genome,
                    ).items()
                },
            ),
        ),
    )


def camelcase_array_structexpression_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
):
    for field in array_structexpression_fields(ht):
        ht = ht.transmute(
            **{
                snake_to_camelcase(field): ht[field].map(
                    lambda c: camelcase_hl_struct(c),
                ),
            },
        )

    # Custom handling of nested sorted_transcript_consequences fields for GRCh38/SNV_INDEL.
    # Note that spliceregion (extended_intronic_splice_region_variant) prevents
    # a more procedural approach here.
    if (
        reference_genome == ReferenceGenome.GRCh38
        and dataset_type == DatasetType.SNV_INDEL
    ):
        ht = ht.annotate(
            sortedTranscriptConsequences=ht.sortedTranscriptConsequences.map(
                lambda s: s.annotate(
                    loftee=camelcase_hl_struct(s.loftee),
                    utrannotator=camelcase_hl_struct(s.utrannotator),
                ),
            ),
        )
    return ht


def unmap_formatting_annotation_enums(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> hl.Table:
    formatting_annotation_names = {
        fa.__name__ for fa in dataset_type.formatting_annotation_fns(reference_genome)
    }
    if 'sorted_motif_feature_consequences' in formatting_annotation_names:
        ht = ht.annotate(
            sorted_motif_feature_consequences=ht.sorted_motif_feature_consequences.map(
                lambda c: c.annotate(
                    consequence_terms=c.consequence_term_ids.map(
                        lambda tid: hl.array(MOTIF_CONSEQUENCE_TERMS)[tid],
                    ),
                ).drop('consequence_term_ids'),
            ),
        )
        ht = ht.annotate_globals(
            enums=ht.enums.drop('sorted_motif_feature_consequences'),
        )
    if 'sorted_regulatory_feature_consequences' in formatting_annotation_names:
        ht = ht.annotate(
            sorted_regulatory_feature_consequences=ht.sorted_regulatory_feature_consequences.map(
                lambda c: c.annotate(
                    biotype=hl.array(REGULATORY_BIOTYPES)[c.biotype_id],
                    consequence_terms=c.consequence_term_ids.map(
                        lambda tid: hl.array(REGULATORY_CONSEQUENCE_TERMS)[tid],
                    ),
                ).drop('biotype_id', 'consequence_term_ids'),
            ),
        )
        ht = ht.annotate_globals(
            enums=ht.enums.drop('sorted_regulatory_feature_consequences'),
        )
    if 'sorted_transcript_consequences' in formatting_annotation_names:
        ht = ht.annotate(
            sorted_transcript_consequences=ht.sorted_transcript_consequences.map(
                lambda c: c.annotate(
                    biotype=hl.array(BIOTYPES)[c.biotype_id],
                    consequence_terms=c.consequence_term_ids.map(
                        lambda tid: hl.array(TRANSCRIPT_CONSEQUENCE_TERMS)[tid],
                    ),
                    **{
                        'loftee': c.loftee.annotate(
                            lof_filters=c.loftee.lof_filter_ids.map(
                                lambda fid: hl.array(LOF_FILTERS)[fid],
                            ),
                        ).drop('lof_filter_ids'),
                        'utrannotator': c.utrannotator.annotate(
                            fiveutr_consequence=hl.array(FIVEUTR_CONSEQUENCES)[
                                c.utrannotator.fiveutr_consequence_id
                            ],
                        ).drop('fiveutr_consequence_id'),
                    }
                    if reference_genome == ReferenceGenome.GRCh38
                    and dataset_type == DatasetType.SNV_INDEL
                    else {
                        'lof_filters': c.lof_filter_ids.map(
                            lambda fid: hl.array(LOF_FILTERS)[fid],
                        ),
                    },
                ).drop(
                    'biotype_id',
                    'consequence_term_ids',
                    *(
                        []
                        if reference_genome == ReferenceGenome.GRCh38
                        and dataset_type == DatasetType.SNV_INDEL
                        else [
                            'lof_filter_ids',
                        ]
                    ),
                ),
            ),
        )
        ht = ht.annotate_globals(enums=ht.enums.drop('sorted_transcript_consequences'))
    if 'mitotip' in formatting_annotation_names:
        ht = ht.annotate(
            mitotip=hl.Struct(
                trna_prediction=hl.array(MITOTIP_PATHOGENICITIES)[
                    ht.mitotip.trna_prediction_id
                ],
            ),
        )
        ht = ht.annotate_globals(enums=ht.enums.drop('mitotip'))
    if 'cpx_intervals' in formatting_annotation_names:
        ht = ht.annotate(
            cpx_intervals=ht.cpx_intervals.map(
                lambda cpx_i: cpx_i.annotate(
                    type=hl.array(SV_TYPES)[cpx_i.type_id],
                ).drop('type_id'),
            ),
        )
    if 'sv_type_id' in formatting_annotation_names:
        ht = ht.annotate(sv_type=hl.array(SV_TYPES)[ht.sv_type_id]).drop('sv_type_id')
        ht = ht.annotate_globals(enums=ht.enums.drop('sv_type'))
    if 'sv_type_detail_id' in formatting_annotation_names:
        ht = ht.annotate(
            sv_type_detail=hl.array(SV_TYPE_DETAILS)[ht.sv_type_detail_id],
        ).drop('sv_type_detail_id')
        ht = ht.annotate_globals(enums=ht.enums.drop('sv_type_detail'))
    if 'sorted_gene_consequences' in formatting_annotation_names:
        ht = ht.annotate(
            sorted_gene_consequences=ht.sorted_gene_consequences.map(
                lambda c: c.annotate(
                    major_consequence=hl.array(SV_CONSEQUENCE_RANKS)[
                        c.major_consequence_id
                    ],
                ).drop('major_consequence_id'),
            ),
        )
        ht = ht.annotate_globals(enums=ht.enums.drop('sorted_gene_consequences'))
    return ht
