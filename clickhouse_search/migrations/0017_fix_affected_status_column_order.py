# Generated manually by the seqr team
import clickhouse_backend.models
import clickhouse_search.backend.fields
from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0016_add_affected_status'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EntriesToProjectGtStatsGRCh37SnvIndel',
        ),
        migrations.CreateModel(
            name='EntriesToProjectGtStatsGRCh37SnvIndel',
            fields=[
                ('project_guid', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('key', clickhouse_search.backend.fields.UInt32FieldDeltaCodecField(primary_key=True, serialize=False)),
                ('sample_type', clickhouse_backend.models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])),
                ('affected', clickhouse_backend.models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])),
                ('ref_samples', clickhouse_backend.models.Int64Field()),
                ('het_samples', clickhouse_backend.models.Int64Field()),
                ('hom_samples', clickhouse_backend.models.Int64Field()),
            ],
            options={
                'db_table': 'GRCh37/SNV_INDEL/entries_to_project_gt_stats_mv',
                'to_table': 'ProjectGtStatsGRCh37SnvIndel',
                'source_table': 'EntriesGRCh37SnvIndel',
                'source_sql': 'ARRAY JOIN calls GROUP BY project_guid, key, sample_type, affected',
                'column_selects': {
                    'affected': "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U')",
                    'het_samples': "sumIf(sign, calls.gt = 'HET')",
                    'hom_samples': "sumIf(sign, calls.gt = 'HOM')",
                    'ref_samples': "sumIf(sign, calls.gt = 'REF')",
                },
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.DeleteModel(
            name='EntriesToProjectGtStatsSnvIndel',
        ),
        migrations.CreateModel(
            name='EntriesToProjectGtStatsSnvIndel',
            fields=[
                ('project_guid', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('key', clickhouse_search.backend.fields.UInt32FieldDeltaCodecField(primary_key=True, serialize=False)),
                ('sample_type', clickhouse_backend.models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])),
                ('affected', clickhouse_backend.models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])),
                ('ref_samples', clickhouse_backend.models.Int64Field()),
                ('het_samples', clickhouse_backend.models.Int64Field()),
                ('hom_samples', clickhouse_backend.models.Int64Field()),
            ],
            options={
                'db_table': 'GRCh38/SNV_INDEL/entries_to_project_gt_stats_mv',
                'to_table': 'ProjectGtStatsSnvIndel',
                'source_table': 'EntriesSnvIndel',
                'source_sql': 'ARRAY JOIN calls GROUP BY project_guid, key, sample_type, affected',
                'column_selects': {
                    'affected': "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U')",
                    'het_samples': "sumIf(sign, calls.gt = 'HET')",
                    'hom_samples': "sumIf(sign, calls.gt = 'HOM')",
                    'ref_samples': "sumIf(sign, calls.gt = 'REF')",
                },
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.DeleteModel(
            name='EntriesToProjectGtStatsMito',
        ),
        migrations.CreateModel(
            name='EntriesToProjectGtStatsMito',
            fields=[
                ('project_guid', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('key', clickhouse_search.backend.fields.UInt32FieldDeltaCodecField(primary_key=True, serialize=False)),
                ('sample_type', clickhouse_backend.models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])),
                ('affected', clickhouse_backend.models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])),
                ('ref_samples', clickhouse_backend.models.Int64Field()),
                ('het_samples', clickhouse_backend.models.Int64Field()),
                ('hom_samples', clickhouse_backend.models.Int64Field()),
            ],
            options={
                'db_table': 'GRCh38/MITO/entries_to_project_gt_stats_mv',
                'to_table': 'ProjectGtStatsMito',
                'source_table': 'EntriesMito',
                'source_sql': 'ARRAY JOIN calls GROUP BY project_guid, key, sample_type, affected',
                'column_selects': {
                    'affected': "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U')",
                    'het_samples': "sumIf(sign, calls.hl > '0' AND calls.hl < '0.95')",
                    'hom_samples': "sumIf(sign, calls.hl >= '0.95')",
                    'ref_samples': "sumIf(sign, calls.hl == '0')",
                },
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.DeleteModel(
            name='EntriesToProjectGtStatsSv',
        ),
        migrations.CreateModel(
            name='EntriesToProjectGtStatsSv',
            fields=[
                ('project_guid', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('key', clickhouse_search.backend.fields.UInt32FieldDeltaCodecField(primary_key=True, serialize=False)),
                ('affected', clickhouse_backend.models.Enum8Field(choices=[(1, 'A'), (2, 'N'), (3, 'U')])),
                ('ref_samples', clickhouse_backend.models.Int64Field()),
                ('het_samples', clickhouse_backend.models.Int64Field()),
                ('hom_samples', clickhouse_backend.models.Int64Field()),
            ],
            options={
                'db_table': 'GRCh38/SV/entries_to_project_gt_stats_mv',
                'to_table': 'ProjectGtStatsSv',
                'source_table': 'EntriesSv',
                'source_sql': 'ARRAY JOIN calls GROUP BY project_guid, key, affected',
                'column_selects': {
                    'affected': "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U')",
                    'het_samples': "sumIf(sign, calls.gt = 'HET')",
                    'hom_samples': "sumIf(sign, calls.gt = 'HOM')",
                    'ref_samples': "sumIf(sign, calls.gt = 'REF')",
                },
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
    ]
