from collections import OrderedDict
import hail as hl

from hail_search.constants import GENOME_VERSION_GRCh38, SCREEN_KEY, PREFILTER_FREQ_CUTOFF, ALPHAMISSENSE_SORT, \
    UTR_ANNOTATOR_KEY, EXTENDED_SPLICE_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY, GENOME_VERSION_GRCh37
from hail_search.queries.base import BaseHailTableQuery, PredictionPath
from hail_search.queries.snv_indel_37 import SnvIndelHailTableQuery37

EXTENDED_SPLICE_REGION_CONSEQUENCE = 'extended_intronic_splice_region_variant'


class SnvIndelHailTableQuery(SnvIndelHailTableQuery37):

    GENOME_VERSION = GENOME_VERSION_GRCh38
    LIFT_GENOME_VERSION = GENOME_VERSION_GRCh37
    PREDICTION_FIELDS_CONFIG = {
        **SnvIndelHailTableQuery37.PREDICTION_FIELDS_CONFIG,
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_score'),
        'mut_pred': PredictionPath('dbnsfp', 'MutPred_score'),
        'vest': PredictionPath('dbnsfp', 'VEST4_score'),
        'gnomad_noncoding': PredictionPath('gnomad_non_coding_constraint', 'z_score'),
    }
    LIFTOVER_ANNOTATION_FIELDS = BaseHailTableQuery.LIFTOVER_ANNOTATION_FIELDS
    ANNOTATION_OVERRIDE_FIELDS = SnvIndelHailTableQuery37.ANNOTATION_OVERRIDE_FIELDS + [
        SCREEN_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY,
    ]
    FREQUENCY_PREFILTER_FIELDS = OrderedDict([
        (True, 0.001),
        ('is_gt_1_percent', PREFILTER_FREQ_CUTOFF),
        ('is_gt_3_percent', 0.03),
        ('is_gt_5_percent', 0.05),
        ('is_gt_10_percent', 0.1),
    ])
    SORTS = {
        **SnvIndelHailTableQuery37.SORTS,
        ALPHAMISSENSE_SORT: lambda r: [
            SnvIndelHailTableQuery37._format_prediction_sort_value(
                hl.min(r.sorted_transcript_consequences.map(lambda t: t.alphamissense.pathogenicity))
            ),
            SnvIndelHailTableQuery37._format_prediction_sort_value(r.selected_transcript.alphamissense.pathogenicity),
        ],
    }

    def _get_allowed_consequence_ids(self, annotations):
        parsed_allowed_consequences = {}
        allowed_consequence_ids = super()._get_allowed_consequence_ids(annotations)
        if allowed_consequence_ids:
            parsed_allowed_consequences[self.TRANSCRIPT_CONSEQUENCE_FIELD] = allowed_consequence_ids

        utr_consequence_ids = self._get_enum_terms_ids(
            self.TRANSCRIPTS_FIELD, subfield='utrannotator', nested_subfield='fiveutr_consequence',
            terms=(annotations.get(UTR_ANNOTATOR_KEY) or []),
        )
        if utr_consequence_ids:
            parsed_allowed_consequences[UTR_ANNOTATOR_KEY] = utr_consequence_ids

        if EXTENDED_SPLICE_REGION_CONSEQUENCE in (annotations.get(EXTENDED_SPLICE_KEY) or []):
            parsed_allowed_consequences[EXTENDED_SPLICE_REGION_CONSEQUENCE] = True

        return parsed_allowed_consequences

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        allowed_consequence_filters = []

        consequence_ids = allowed_consequence_ids.get(SnvIndelHailTableQuery37.TRANSCRIPT_CONSEQUENCE_FIELD)
        if consequence_ids:
            allowed_consequence_filters.append(SnvIndelHailTableQuery37._get_allowed_transcripts_filter(consequence_ids))

        utr_consequences = allowed_consequence_ids.get(UTR_ANNOTATOR_KEY)
        if utr_consequences:
            utr_consequences = hl.set(utr_consequences)
            allowed_consequence_filters.append(lambda tc: utr_consequences.contains(tc.utrannotator.fiveutr_consequence_id))

        if allowed_consequence_ids.get(EXTENDED_SPLICE_REGION_CONSEQUENCE):
            allowed_consequence_filters.append(lambda tc: tc.spliceregion.extended_intronic_splice_region_variant)

        return allowed_consequence_filters[0] if len(allowed_consequence_filters) == 1 else lambda tc: hl.any([
            f(tc) for f in allowed_consequence_filters
        ])

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = super()._get_annotation_override_filters(ht, annotation_overrides)

        if annotation_overrides.get(SCREEN_KEY):
            allowed_consequences = hl.set(self._get_enum_terms_ids(SCREEN_KEY.lower(), 'region_type', annotation_overrides[SCREEN_KEY]))
            annotation_filters.append(allowed_consequences.contains(ht.screen.region_type_ids.first()))

        for feature_key in [MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY]:
            if annotation_overrides.get(feature_key):
                field = f'sorted_{feature_key}_consequences'
                allowed_consequences = hl.set(self._get_enum_terms_ids(
                    field, self.TRANSCRIPT_CONSEQUENCE_FIELD, annotation_overrides[feature_key]),
                )
                annotation_filters.append(
                    ht[field].any(lambda c: c.consequence_term_ids.any(allowed_consequences.contains))
                )

        return annotation_filters

    @staticmethod
    def _lookup_variant_annotations():
        return {'liftover_locus': lambda r: r.rg37_locus}
