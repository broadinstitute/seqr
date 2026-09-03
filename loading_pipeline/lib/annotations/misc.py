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
from loading_pipeline.lib.core import DatasetType
from loading_pipeline.lib.core.definitions import ReferenceGenome


def annotate_formatting_annotation_enum_globals(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> hl.Table:
    ht = ht.select_globals(
        enums=hl.Struct(),
    )
    formatting_annotation_names = {
        fa.__name__ for fa in dataset_type.formatting_annotation_fns(reference_genome)
    }
    if 'sorted_motif_feature_consequences' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                sorted_motif_feature_consequences=hl.Struct(
                    consequence_term=MOTIF_CONSEQUENCE_TERMS,
                ),
            ),
        )
    if 'sorted_regulatory_feature_consequences' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                sorted_regulatory_feature_consequences=hl.Struct(
                    biotype=REGULATORY_BIOTYPES,
                    consequence_term=REGULATORY_CONSEQUENCE_TERMS,
                ),
            ),
        )
    if 'sorted_transcript_consequences' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                sorted_transcript_consequences=hl.Struct(
                    biotype=BIOTYPES,
                    consequence_term=TRANSCRIPT_CONSEQUENCE_TERMS,
                    **(
                        {
                            'loftee': hl.Struct(
                                lof_filter=LOF_FILTERS,
                            ),
                            'utrannotator': hl.Struct(
                                fiveutr_consequence=FIVEUTR_CONSEQUENCES,
                            ),
                        }
                        if reference_genome == ReferenceGenome.GRCh38
                        and dataset_type == DatasetType.SNV_INDEL
                        else {
                            'lof_filter': LOF_FILTERS,
                        }
                    ),
                ),
            ),
        )
    if 'mitotip' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                mitotip=hl.Struct(
                    trna_prediction=MITOTIP_PATHOGENICITIES,
                ),
            ),
        )
    if 'sv_type_id' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                sv_type=SV_TYPES,
            ),
        )
    if 'sv_type_detail_id' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(sv_type_detail=SV_TYPE_DETAILS),
        )
    if 'sorted_gene_consequences' in formatting_annotation_names:
        ht = ht.annotate_globals(
            enums=ht.enums.annotate(
                sorted_gene_consequences=hl.Struct(
                    major_consequence=SV_CONSEQUENCE_RANKS,
                ),
            ),
        )
    return ht
