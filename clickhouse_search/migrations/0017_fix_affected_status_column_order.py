# Generated manually by the seqr team
from django.db import migrations
from string import Template

ENTRIES_TO_PROJECT_GT_STATS = Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/entries_to_project_gt_stats_mv`
TO `$reference_genome/$dataset_type/project_gt_stats`
AS SELECT
    project_guid,
    key,
    $columns
FROM `$reference_genome/$dataset_type/entries`
ARRAY JOIN calls
GROUP BY $groupby_columns
""")

class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0016_add_affected_status'),
    ]

    operations = [
        migrations.RunSQL(
            'DROP TABLE `GRCh37/SNV_INDEL/entries_to_project_gt_stats_mv`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    'sample_type',
                    "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') affected",
                    "sumIf(sign, calls.gt = 'REF') ref_samples",
                    "sumIf(sign, calls.gt = 'HET') het_samples",
                    "sumIf(sign, calls.gt = 'HOM') hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type, affected',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP TABLE `GRCh38/SNV_INDEL/entries_to_project_gt_stats_mv`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
                columns=",\n    ".join([
                    'sample_type',
                    "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') affected",
                    "sumIf(sign, calls.gt = 'REF') ref_samples",
                    "sumIf(sign, calls.gt = 'HET') het_samples",
                    "sumIf(sign, calls.gt = 'HOM') hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type, affected',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP TABLE `GRCh38/MITO/entries_to_project_gt_stats_mv`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
                columns=",\n    ".join([
                    'sample_type',
                    "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') affected",
                    "sumIf(sign, calls.hl == '0') ref_samples",
                    "sumIf(sign, calls.hl > '0' AND calls.hl < '0.95') het_samples",
                    "sumIf(sign, calls.hl >= '0.95') hom_samples",
                ]),
                groupby_columns='project_guid, key, sample_type, affected',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP TABLE `GRCh38/SV/entries_to_project_gt_stats_mv`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            ENTRIES_TO_PROJECT_GT_STATS.substitute(
                reference_genome='GRCh38',
                dataset_type='SV',
                columns=",\n    ".join([
                    "dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') affected",
                    "sumIf(sign, calls.gt = 'REF') ref_samples",
                    "sumIf(sign, calls.gt = 'HET') het_samples",
                    "sumIf(sign, calls.gt = 'HOM') hom_samples",
                ]),
                groupby_columns='project_guid, key, affected',
            ),
            hints={'clickhouse': True},
        ),
    ]
