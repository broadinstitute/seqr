import os
from string import Template


CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS  = os.environ.get(
    'CLICKHOUSE_AC_EXCLUDED_PROJECT_GUIDS',
    ''
).split(',')
CLICKHOUSE_WRITER_PASSWORD = os.environ.get('CLICKHOUSE_WRITER_PASSWORD', 'clickhouse_test')
CLICKHOUSE_WRITER_USER = os.environ.get('CLICKHOUSE_WRITER_USER', 'clickhouse')

GT_STATS_DICT = Template(Template("""
CREATE DICTIONARY `$reference_genome/$dataset_type/gt_stats_dict`
(
    key UInt32,
    $columns
)
PRIMARY KEY key
SOURCE(CLICKHOUSE(USER $clickhouse_writer_user PASSWORD $clickhouse_writer_password TABLE `$reference_genome/$dataset_type/gt_stats`))
LIFETIME(MIN 0 MAX 0)
LAYOUT(FLAT(MAX_ARRAY_SIZE $size))
""").safe_substitute(
    # Note the nested Template-ing that allows
    # double substitution these shared values
    clickhouse_writer_user=CLICKHOUSE_WRITER_USER,
    clickhouse_writer_password=CLICKHOUSE_WRITER_PASSWORD,
))