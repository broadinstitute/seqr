import hail as hl

from loading_pipeline.lib.core import ReferenceGenome


def sorted_hl_struct(s: hl.StructExpression) -> hl.StructExpression:
    if not isinstance(s, hl.StructExpression):
        return s
    return s.select(**{k: sorted_hl_struct(s[k]) for k in sorted(s)})


def reformat_transcripts_for_export(i: int, s: hl.StructExpression):
    formatted_s = s.annotate(
        majorConsequence=s.consequenceTerms.first(),
        transcriptRank=i,
    )
    return sorted_hl_struct(formatted_s)


def subset_consequences_fields(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
) -> hl.Table:
    if reference_genome == ReferenceGenome.GRCh38:
        return ht.annotate(
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
                lambda c: c.select(
                    'canonical',
                    'consequenceTerms',
                    'geneId',
                    alphamissensePathogenicity=c.alphamissense.pathogenicity,
                    extendedIntronicSpliceRegionVariant=c.spliceregion.extendedIntronicSpliceRegionVariant,
                    fiveutrConsequence=c.utrannotator.fiveutrConsequence,
                    isManeSelect=hl.is_defined(c.maneSelect),
                ),
            ),
        )
    return ht.annotate(
        sortedTranscriptConsequences=ht.sortedTranscriptConsequences.map(
            lambda c: c.select(
                'canonical',
                'consequenceTerms',
                'geneId',
            ),
        ),
    )
