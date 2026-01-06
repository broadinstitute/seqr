from clickhouse_backend import models
from django.db.migrations import state
from django.db.models import options

from clickhouse_search.backend.table_models import MATERIALIZED_VIEW_META_FIELDS, DICTIONARY_META_FIELDS
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample

options.DEFAULT_NAMES = (
    *options.DEFAULT_NAMES,
    'projection',
    *MATERIALIZED_VIEW_META_FIELDS,
    *DICTIONARY_META_FIELDS,
)
state.DEFAULT_NAMES = options.DEFAULT_NAMES

class ClickHouseRouter:
    """
    Adapted from https://github.com/jayvynl/django-clickhouse-backend/blob/v1.3.2/README.md#configuration
    """

    def __init__(self):
        self.route_model_names = set()
        for model in self._get_subclasses(models.ClickhouseModel):
            if model._meta.abstract:
                continue
            self.route_model_names.add(model._meta.label_lower)

    @staticmethod
    def _get_subclasses(class_):
        classes = class_.__subclasses__()

        index = 0
        while index < len(classes):
            classes.extend(classes[index].__subclasses__())
            index += 1

        return list(set(classes))

    def db_for_read(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def db_for_write(self, model, **hints):
        # When using Clickhouse models, the default connection routing used for writes will attempt to use read-only
        # credentials and fail. This is by design to prevent accidental writes. To write to Clickhouse, explicitly
        # set my_queryset.using('clickhouse_write') before executing a write operation
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'clickhouse_search' or hints.get('clickhouse'):
            return db == 'clickhouse_write'
        elif db in {'clickhouse', 'clickhouse_write'}:
            return False
        return None

# Import models here to register them for django management as part of the clickhouse_search app

from clickhouse_search.models.gt_stats_models import (
    ProjectsToGtStatsGRCh37SnvIndel,
    ProjectsToGtStatsSnvIndel,
    ProjectsToGtStatsMito,
    ProjectsToGtStatsSv,
    GtStatsDictGRCh37SnvIndel,
    GtStatsDictSnvIndel,
    GtStatsDictMito,
    GtStatsDictSv,
)
from clickhouse_search.models.search_models import (
    AnnotationsGRCh37SnvIndel,
    AnnotationsMito,
    AnnotationsSnvIndel,
    AnnotationsSv,
    AnnotationsGcnv,
    EntriesGRCh37SnvIndel,
    EntriesMito,
    EntriesSnvIndel,
    EntriesSv,
    EntriesGcnv,
    KeyLookupGRCh37SnvIndel,
    KeyLookupMito,
    KeyLookupSnvIndel,
    KeyLookupSv,
    KeyLookupGcnv,
    TranscriptsGRCh37SnvIndel,
    TranscriptsSnvIndel,
    ProjectPartitionsSnvIndel,
    ProjectPartitionsDict,
    SexDict,
    AffectedDict,
    GeneIdDict,
)

ENTRY_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: EntriesGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: EntriesSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: EntriesMito,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}': EntriesSv,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}': EntriesGcnv,
    },
}
ANNOTATIONS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: AnnotationsGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: AnnotationsSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: AnnotationsMito,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}': AnnotationsSv,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}': AnnotationsGcnv,
    },
}
TRANSCRIPTS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: TranscriptsGRCh37SnvIndel,
    GENOME_VERSION_GRCh38: TranscriptsSnvIndel,
}
KEY_LOOKUP_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: KeyLookupGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: KeyLookupSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: KeyLookupMito,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}': KeyLookupSv,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}': KeyLookupGcnv,
    },
}
PROJECT_GT_STATS_VIEW_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: ProjectsToGtStatsGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: ProjectsToGtStatsSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: ProjectsToGtStatsMito,
        Sample.DATASET_TYPE_SV_CALLS: ProjectsToGtStatsSv,
    },
}
GT_STATS_DICT_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: GtStatsDictGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: GtStatsDictSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: GtStatsDictMito,
        Sample.DATASET_TYPE_SV_CALLS: GtStatsDictSv,
    },
}
