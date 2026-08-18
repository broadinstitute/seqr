from collections import OrderedDict

import hail as hl

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
