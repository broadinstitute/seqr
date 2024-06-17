from collections import OrderedDict
import hail as hl

from hail_search.constants import GENOME_VERSION_GRCh38, SCREEN_KEY, PREFILTER_FREQ_CUTOFF, ALPHAMISSENSE_SORT
from hail_search.queries.base import BaseHailTableQuery, PredictionPath
from hail_search.queries.snv_indel_37 import SnvIndelHailTableQuery37

EXTENDED_SPLICE_REGION_CONSEQUENCE = 'extended_intronic_splice_region_variant'
UTR_ANNOTATOR_KEY = 'UTRAnnotator'


class SnvIndelHailTableQuery(SnvIndelHailTableQuery37):

    GENOME_VERSION = GENOME_VERSION_GRCh38
    PREDICTION_FIELDS_CONFIG = {
        **SnvIndelHailTableQuery37.PREDICTION_FIELDS_CONFIG,
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_score'),
        'mut_pred': PredictionPath('dbnsfp', 'MutPred_score'),
        'vest': PredictionPath('dbnsfp', 'VEST4_score'),
        'gnomad_noncoding': PredictionPath('gnomad_non_coding_constraint', 'z_score'),
    }
    LIFTOVER_ANNOTATION_FIELDS = BaseHailTableQuery.LIFTOVER_ANNOTATION_FIELDS
    ANNOTATION_OVERRIDE_FIELDS = SnvIndelHailTableQuery37.ANNOTATION_OVERRIDE_FIELDS + [SCREEN_KEY]
    FREQUENCY_PREFILTER_FIELDS = OrderedDict([
        (True, PREFILTER_FREQ_CUTOFF),
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
        return {
            self.TRANSCRIPT_CONSEQUENCE_FIELD: super()._get_allowed_consequence_ids(annotations),
            EXTENDED_SPLICE_REGION_CONSEQUENCE: EXTENDED_SPLICE_REGION_CONSEQUENCE in (annotations.get('extended_splice_site') or []),
            UTR_ANNOTATOR_KEY: self._get_enum_terms_ids(
                self.TRANSCRIPTS_FIELD, subfield='utrannotator', nested_subfield='fiveutr_consequence',
                terms=(annotations.get(UTR_ANNOTATOR_KEY) or []),
            )
        }

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        allowed_consequence_filters = [SnvIndelHailTableQuery37._get_allowed_transcripts_filter(
            allowed_consequence_ids[SnvIndelHailTableQuery37.TRANSCRIPT_CONSEQUENCE_FIELD]
        )]

        if allowed_consequence_ids[EXTENDED_SPLICE_REGION_CONSEQUENCE]:
            allowed_consequence_filters.append(lambda tc: tc.spliceregion.extended_intronic_splice_region_variant)

        if allowed_consequence_ids[UTR_ANNOTATOR_KEY]:
            utr_consequences = hl.set(allowed_consequence_ids[UTR_ANNOTATOR_KEY])
            allowed_consequence_filters.append(lambda tc: utr_consequences.contains(tc.utrannotator.fiveutr_consequence_id))

        return allowed_consequence_filters[0] if len(allowed_consequence_filters) == 1 else lambda tc: hl.any([
            f(tc) for f in allowed_consequence_filters
        ])

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = super()._get_annotation_override_filters(ht, annotation_overrides)

        if annotation_overrides.get(SCREEN_KEY):
            allowed_consequences = hl.set(self._get_enum_terms_ids(SCREEN_KEY.lower(), 'region_type', annotation_overrides[SCREEN_KEY]))
            annotation_filters.append(allowed_consequences.contains(ht.screen.region_type_ids.first()))

        return annotation_filters
