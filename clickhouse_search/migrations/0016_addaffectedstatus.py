# Generated manually by the seqr team.

import clickhouse_backend.models
import clickhouse_search.backend.engines
import clickhouse_search.backend.fields
import clickhouse_search.models

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import os
from string import Template

from clickhouse_search.migrations.shared import GT_STATS_DICT

SEQRDB_AFFECTED_STATUS_DICT = """
CREATE DICTIONARY `seqrdb_affected_status_dict`
(
    `family_guid` String,
    `sampleId` String,
    `affected` String
)
PRIMARY KEY key
SOURCE(POSTGRESQL(
    NAME 'seqr_postgres_named_collection' 
    DATABASE 'seqrdb' 
    QUERY 'select f.guid as family_guid, i.individual_id as sample_id, i.affected FROM seqr_individual i INNER JOIN seqr_family f ON i.family_id = f.id'
))
LIFETIME(MIN 0 MAX 0)
LAYOUT(COMPLEX_KEY_HASHED());
"""


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        '0015_remove_gnomadgenomessnvindel_key_and_more'
    ]

    operations = [
        migrations.RunSQL(
            SEQRDB_AFFECTED_STATUS_DICT,
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP DICTIONARY `GRCh37/SNV_INDEL/gt_stats_dict`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
                columns= ",\n    ".join([
                    'ac_wes UInt32',
                    'ac_wgs UInt32',
                    'ac_affected UInt32',
                    'hom_wes UInt32',
                    'hom_wgs UInt32',
                    'hom_affected UInt32',
                ]),
                size=int(2e8),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP DICTIONARY `GRCh38/SNV_INDEL/gt_stats_dict`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
                columns= ",\n    ".join([
                    'ac_wes UInt32',
                    'ac_wgs UInt32',
                    'ac_affected UInt32',
                    'hom_wes  UInt32',
                    'hom_wgs  UInt32',
                    'hom_affected UInt32',
                ]),
                size=int(1e9),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP DICTIONARY `GRCh38/MITO/gt_stats_dict`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
                columns= ",\n    ".join([
                    'ac_het_wes UInt32',
                    'ac_het_wgs UInt32',
                    'ac_het_affected UInt32',
                    'ac_hom_wes UInt32',
                    'ac_hom_wgs UInt32',
                    'ac_hom_affected UInt32',
                ]),
                size=int(1e6),
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            'DROP DICTIONARY `GRCh38/SV/gt_stats_dict`',
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            GT_STATS_DICT.substitute(
                reference_genome='GRCh38',
                dataset_type='SV',
                columns= ",\n    ".join([
                    'ac_wgs UInt32',
                    'ac_affected UInt32',
                    'hom_wgs UInt32',
                    'hom_affected UInt32',
                ]),
                size=int(5e6),
            ),
            hints={'clickhouse': True},
        )
    ]

