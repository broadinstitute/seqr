# Generated manually by the seqr team.
import os
from string import Template

from django.db import migrations

from settings import DATABASES

CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS  = os.environ.get(
    'CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS',
    ''
).split(',')
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'clickhouse')
CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', 'clickhouse_test')

ENTRIES_TO_PROJECT_GT_STATS = Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/entries_to_project_gt_stats_mv`
TO `$reference_genome/$dataset_type/project_gt_stats`
AS SELECT
    project_guid,
    key,
    $columns
FROM `$reference_genome/$dataset_type/entries`
GROUP BY $groupby_columns
""")

PROJECT_GT_STATS_TO_GT_STATS = Template(Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/project_gt_stats_to_gt_stats_mv`
REFRESH EVERY 10 YEAR
TO `$reference_genome/$dataset_type/gt_stats`
AS SELECT
    key,
    $columns
FROM `$reference_genome/$dataset_type/project_gt_stats`
WHERE project_guid NOT IN $clickhouse_ac_excluded_project_guids
GROUP BY key
""").safe_substitute(
    clickhouse_ac_excluded_project_guids=CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS
))

GT_STATS_DICT = Template(Template("""
CREATE DICTIONARY `$reference_genome/$dataset_type/gt_stats_dict`
(
    key UInt32,
    $columns
)
PRIMARY KEY key
SOURCE(CLICKHOUSE(USER $clickhouse_user PASSWORD $clickhouse_password DB $clickhouse_database TABLE `$reference_genome/$dataset_type/gt_stats`))
LIFETIME(MIN 0 MAX 0)
LAYOUT(FLAT(MAX_ARRAY_SIZE $size))
""").safe_substitute(
    # Note the nested Template-ing that allows
    # double substitution these shared values
    clickhouse_user=CLICKHOUSE_USER,
    clickhouse_password=CLICKHOUSE_PASSWORD,
    clickhouse_database=DATABASES.get('clickhouse', {}).get('NAME'),
))

class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0008_gtstatsgrch37snvindel_gtstatsmito_gtstatssnvindel_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    'sample_type',
                    "sum(toInt32(arrayCount(s -> (s.gt = 'REF'), calls) * sign)) AS ref_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HET'), calls) * sign)) AS het_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HOM'), calls) * sign)) AS hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            PROJECT_GT_STATS_TO_GT_STATS.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WES') AS ac_wes",
                    "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WGS') AS ac_wgs",
                    "sumIf(hom_samples, sample_type = 'WES') AS hom_wes",
                    "sumIf(hom_samples, sample_type = 'WGS') AS hom_wgs",
                ])
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
                columns= ",\n    ".join([
                    'ac_wes UInt32',
                    'ac_wgs UInt32',
                    'hom_wes UInt32',
                    'hom_wgs UInt32',
                ]),
                size=int(2e8),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    'sample_type',
                    "sum(toInt32(arrayCount(s -> (s.gt = 'REF'), calls) * sign)) AS ref_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HET'), calls) * sign)) AS het_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HOM'), calls) * sign)) AS hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            PROJECT_GT_STATS_TO_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WES') AS ac_wes",
                    "sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WGS') AS ac_wgs",
                    "sumIf(hom_samples, sample_type = 'WES') AS hom_wes",
                    "sumIf(hom_samples, sample_type = 'WGS') AS hom_wgs",
                ])
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
                columns= ",\n    ".join([
                    'ac_wes UInt32',
                    'ac_wgs UInt32',
                    'hom_wes  UInt32',
                    'hom_wgs  UInt32',
                ]),
                size=int(1e9),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
                columns=",\n    ".join([
                    'sample_type',
                    "sum(toInt32(arrayCount(s -> (s.hl == '0'), calls) * sign)) AS ref_samples",
                    "sum(toInt32(arrayCount(s -> (s.hl > '0' AND s.hl < '0.95'), calls) * sign)) AS het_samples",
                    "sum(toInt32(arrayCount(s -> (s.hl >= '0.95'), calls) * sign)) AS hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            PROJECT_GT_STATS_TO_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
                columns=",\n    ".join([
                    "sumIf(het_samples, sample_type = 'WES') AS ac_het_wes",
                    "sumIf(het_samples, sample_type = 'WGS') AS ac_het_wgs",
                    "sumIf(hom_samples, sample_type = 'WES') AS ac_hom_wes",
                    "sumIf(hom_samples, sample_type = 'WGS') AS ac_hom_wgs",
                ])
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
                columns= ",\n    ".join([
                    'ac_het_wes UInt32',
                    'ac_het_wgs UInt32',
                    'ac_hom_wes UInt32',
                    'ac_hom_wgs UInt32',
                ]),
                size=int(1e6),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SV',
                columns=",\n    ".join([
                    "sum(toInt32(arrayCount(s -> (s.gt = 'REF'), calls) * sign)) AS ref_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HET'), calls) * sign)) AS het_samples",
                    "sum(toInt32(arrayCount(s -> (s.gt = 'HOM'), calls) * sign)) AS hom_samples",
                ]),
                groupby_columns='project_guid, key',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            PROJECT_GT_STATS_TO_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SV',
                columns = ",\n    ".join([
                    'sum((het_samples * 1) + (hom_samples * 2)) AS ac_wgs',
                    'sum(hom_samples) AS hom_wgs',
                ]),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='SV',
                columns= ",\n    ".join([
                    'ac_wgs UInt32',
                    'hom_wgs UInt32'
                ]),
                size=int(5e6),
            ),
            hints={'clickhouse': True},
        ),
    ]

