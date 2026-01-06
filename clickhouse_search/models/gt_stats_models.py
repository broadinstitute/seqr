from clickhouse_backend import models
from django.db.models import OneToOneField, CASCADE

from clickhouse_search.backend.fields import UInt32FieldDeltaCodecField
from clickhouse_search.backend.table_models import MaterializedView, Dictionary
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample


class BaseProjectGtStats(models.ClickhouseModel):
    project_guid = models.StringField(low_cardinality=True)
    affected = models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])
    ref_samples = models.UInt32Field()
    het_samples = models.UInt32Field()
    hom_samples = models.UInt32Field()

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by=('project_guid', 'key', 'affected'),
            partition_by='project_guid',
            index_granularity=8192,
        )

class BaseProjectGtStatsMitoSnvIndel(BaseProjectGtStats):
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by=('project_guid', 'key', 'sample_type', 'affected'),
            partition_by='project_guid',
            index_granularity=8192,
        )

class BaseEntriesToProjectGtStats(MaterializedView):
    project_guid = models.StringField(low_cardinality=True)
    key = UInt32FieldDeltaCodecField(primary_key=True)
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    affected = models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])
    ref_samples = models.Int64Field()
    het_samples = models.Int64Field()
    hom_samples = models.Int64Field()

    class Meta:
        abstract = True

class EntriesToProjectGtStatsMeta:
    column_selects = {
        'affected': "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U')",
        'ref_samples': "sumIf(sign, calls.gt = 'REF')",
        'het_samples': "sumIf(sign, calls.gt = 'HET')",
        'hom_samples': "sumIf(sign, calls.gt = 'HOM')",
    }
    source_sql = 'ARRAY JOIN calls GROUP BY project_guid, key, sample_type, affected'

class ProjectGtStatsGRCh37SnvIndel(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh37/SNV_INDEL/project_gt_stats'

class EntriesToProjectGtStatsGRCh37SnvIndel(BaseEntriesToProjectGtStats):

    class Meta(EntriesToProjectGtStatsMeta):
        db_table = 'GRCh37/SNV_INDEL/entries_to_project_gt_stats_mv'
        to_table = 'ProjectGtStatsGRCh37SnvIndel'
        source_table = 'EntriesGRCh37SnvIndel'

class ProjectGtStatsSnvIndel(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh38/SNV_INDEL/project_gt_stats'

class EntriesToProjectGtStatsSnvIndel(BaseEntriesToProjectGtStats):

    class Meta(EntriesToProjectGtStatsMeta):
        db_table = 'GRCh38/SNV_INDEL/entries_to_project_gt_stats_mv'
        to_table = 'ProjectGtStatsSnvIndel'
        source_table = 'EntriesSnvIndel'

class ProjectGtStatsMito(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh38/MITO/project_gt_stats'

class EntriesToProjectGtStatsMito(BaseEntriesToProjectGtStats):

    class Meta(EntriesToProjectGtStatsMeta):
        db_table = 'GRCh38/MITO/entries_to_project_gt_stats_mv'
        to_table = 'ProjectGtStatsMito'
        source_table = 'EntriesMito'
        column_selects = {
            'affected': EntriesToProjectGtStatsMeta.column_selects['affected'],
            'ref_samples': "sumIf(sign, calls.hl == '0')",
            'het_samples': "sumIf(sign, calls.hl > '0' AND calls.hl < '0.95')",
            'hom_samples': "sumIf(sign, calls.hl >= '0.95')",
        }

class ProjectGtStatsSv(BaseProjectGtStats):
    key = OneToOneField('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStats.Meta):
        db_table = 'GRCh38/SV/project_gt_stats'

class EntriesToProjectGtStatsSv(MaterializedView):
    project_guid = models.StringField(low_cardinality=True)
    key = UInt32FieldDeltaCodecField(primary_key=True)
    affected = models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])
    ref_samples = models.Int64Field()
    het_samples = models.Int64Field()
    hom_samples = models.Int64Field()

    class Meta(EntriesToProjectGtStatsMeta):
        db_table = 'GRCh38/SV/entries_to_project_gt_stats_mv'
        to_table = 'ProjectGtStatsSv'
        source_table = 'EntriesSv'
        source_sql = 'ARRAY JOIN calls GROUP BY project_guid, key, affected'


class BaseGtStats(models.ClickhouseModel):
    ac_wes = models.UInt32Field()
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wes = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by='key',
            index_granularity=8192,
        )

class GtStatsGRCh37SnvIndel(BaseGtStats):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh37/SNV_INDEL/gt_stats'

class GtStatsSnvIndel(BaseGtStats):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/SNV_INDEL/gt_stats'

class GtStatsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac_het_wes = models.UInt32Field()
    ac_het_wgs = models.UInt32Field()
    ac_het_affected = models.UInt32Field()
    ac_hom_wes = models.UInt32Field()
    ac_hom_wgs = models.UInt32Field()
    ac_hom_affected = models.UInt32Field()

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/MITO/gt_stats'

class GtStatsSv(models.ClickhouseModel):
    key = OneToOneField('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/SV/gt_stats'

class BaseProjectsToGtStats(MaterializedView):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    ac_wes = models.UInt32Field()
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wes = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta:
        abstract = True

class ProjectsToGtStatsMeta:
    column_selects = {
        'ac_wes': "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WES')",
        'ac_wgs': "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WGS')",
        'ac_affected': "sumIf((het_samples * 1) + (hom_samples * 2), affected = 'A')",
        'hom_wes': "sumIf(hom_samples, sample_type = 'WES')",
        'hom_wgs': "sumIf(hom_samples, sample_type = 'WGS')",
        'hom_affected': "sumIf(hom_samples, affected = 'A')",
    }
    source_sql = 'WHERE project_guid NOT IN {CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS} GROUP BY key'
    refreshable = True

class ProjectsToGtStatsGRCh37SnvIndel(BaseProjectsToGtStats):

    class Meta(ProjectsToGtStatsMeta):
        db_table = 'GRCh37/SNV_INDEL/project_gt_stats_to_gt_stats_mv'
        to_table = 'GtStatsGRCh37SnvIndel'
        source_table = 'ProjectGtStatsGRCh37SnvIndel'

class ProjectsToGtStatsSnvIndel(BaseProjectsToGtStats):

    class Meta(ProjectsToGtStatsMeta):
        db_table = 'GRCh38/SNV_INDEL/project_gt_stats_to_gt_stats_mv'
        to_table = 'GtStatsSnvIndel'
        source_table = 'ProjectGtStatsSnvIndel'

class ProjectsToGtStatsMito(MaterializedView):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    ac_het_wes = models.UInt32Field()
    ac_het_wgs = models.UInt32Field()
    ac_het_affected = models.UInt32Field()
    ac_hom_wes = models.UInt32Field()
    ac_hom_wgs = models.UInt32Field()
    ac_hom_affected = models.UInt32Field()

    class Meta(ProjectsToGtStatsMeta):
        db_table = 'GRCh38/MITO/project_gt_stats_to_gt_stats_mv'
        to_table = 'GtStatsMito'
        source_table = 'ProjectGtStatsMito'
        column_selects = {
            'ac_het_wes': "sumIf(het_samples, sample_type = 'WES')",
            'ac_het_wgs': "sumIf(het_samples, sample_type = 'WGS')",
            'ac_het_affected': "sumIf(het_samples, affected = 'A')",
            'ac_hom_wes': "sumIf(hom_samples, sample_type = 'WES')",
            'ac_hom_wgs': "sumIf(hom_samples, sample_type = 'WGS')",
            'ac_hom_affected': "sumIf(hom_samples, affected = 'A')",
        }


class ProjectsToGtStatsSv(MaterializedView):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta(ProjectsToGtStatsMeta):
        db_table = 'GRCh38/SV/project_gt_stats_to_gt_stats_mv'
        to_table = 'GtStatsSv'
        source_table = 'ProjectGtStatsSv'
        column_selects = {
            'ac_wgs': 'sum((het_samples * 1) + (hom_samples * 2))',
            'ac_affected': "sumIf((het_samples * 1) + (hom_samples * 2), affected = 'A')",
            'hom_wgs': 'sum(hom_samples)',
            'hom_affected': "sumIf(hom_samples, affected = 'A')",
        }


class BaseGtStatsDict(Dictionary):
    key = models.UInt32Field(primary_key=True)
    ac_wes = models.UInt32Field()
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wes = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta:
        abstract = True

class GtStatsDictMeta:
    engine = models.MergeTree(primary_key='key')

class GtStatsDictGRCh37SnvIndel(BaseGtStatsDict):

    class Meta(GtStatsDictMeta):
        db_table = 'GRCh37/SNV_INDEL/gt_stats_dict'
        source_table = 'GtStatsGRCh37SnvIndel'
        layout = 'FLAT(MAX_ARRAY_SIZE 200000000)'

class GtStatsDictSnvIndel(BaseGtStatsDict):

    class Meta(GtStatsDictMeta):
        db_table = 'GRCh38/SNV_INDEL/gt_stats_dict'
        source_table = 'GtStatsSnvIndel'
        layout = 'FLAT(MAX_ARRAY_SIZE 1000000000)'

class GtStatsDictMito(Dictionary):
    key = models.UInt32Field(primary_key=True)
    ac_het_wes = models.UInt32Field()
    ac_het_wgs = models.UInt32Field()
    ac_het_affected = models.UInt32Field()
    ac_hom_wes = models.UInt32Field()
    ac_hom_wgs = models.UInt32Field()
    ac_hom_affected = models.UInt32Field()

    class Meta(GtStatsDictMeta):
        db_table = 'GRCh38/MITO/gt_stats_dict'
        source_table = 'GtStatsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1000000)'

class GtStatsDictSv(Dictionary):
    key = models.UInt32Field(primary_key=True)
    ac_wgs = models.UInt32Field()
    ac_affected = models.UInt32Field()
    hom_wgs = models.UInt32Field()
    hom_affected = models.UInt32Field()

    class Meta(GtStatsDictMeta):
        db_table = 'GRCh38/SV/gt_stats_dict'
        source_table = 'GtStatsSv'
        layout = 'FLAT(MAX_ARRAY_SIZE 5000000)'

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