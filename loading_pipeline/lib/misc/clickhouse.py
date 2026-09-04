import ast
import functools
import hashlib
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from string import Template

from clickhouse_driver import Client

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.retry import retry
from loading_pipeline.lib.paths import (
    existing_variants_parquet_path,
    new_entries_parquet_path,
    new_variant_details_parquet_path,
    new_variants_parquet_path,
)

logger = get_logger(__name__)

GCS_NAMED_COLLECTION = 'pipeline_data_access'
GOOGLE_XML_API_PATH = 'https://storage.googleapis.com/'
OPTIMIZE_TABLE_TIMEOUT_S = 99999
WAIT_VIEW_TIMEOUT_S = 900
REDACTED = 'REDACTED'
STAGING_CLICKHOUSE_DATABASE = 'staging'


class ClickHouseTable(StrEnum):
    KEY_LOOKUP = 'key_lookup'
    VARIANT_DETAILS = 'variants/details'
    VARIANTS_DISK = 'variants_disk'
    VARIANTS_MEMORY = 'variants_memory'
    ENTRIES = 'entries'
    PROJECT_GT_STATS = 'project_gt_stats'
    GT_STATS = 'gt_stats'
    EXISTING_VARIANTS = 'existing_variants'

    @property
    def src_path_fn(self) -> Callable:
        return {
            ClickHouseTable.VARIANTS_DISK: new_variants_parquet_path,
            ClickHouseTable.VARIANTS_MEMORY: new_variants_parquet_path,
            ClickHouseTable.KEY_LOOKUP: (
                lambda *args: new_variant_details_parquet_path(*args)
                if args[1].should_write_new_variant_details
                else new_variants_parquet_path(*args)
            ),
            ClickHouseTable.VARIANT_DETAILS: new_variant_details_parquet_path,
            ClickHouseTable.ENTRIES: new_entries_parquet_path,
            ClickHouseTable.EXISTING_VARIANTS: existing_variants_parquet_path,
        }[self]

    @property
    def key_field(self):
        return 'variantId' if self == ClickHouseTable.KEY_LOOKUP else 'key'

    @property
    def join_condition(self):
        return (
            'assumeNotNull(src.variantId) = dst.variantId'
            if self == ClickHouseTable.KEY_LOOKUP
            else 'assumeNotNull(toUInt32(src.key)) = dst.key'
        )

    @property
    def select_fields(self) -> str:
        return {
            ClickHouseTable.KEY_LOOKUP: 'variantId, key',
        }.get(self, '*')

    @property
    def insert(self) -> Callable:
        return {
            # Note that VARIANTS_DETAILS is not included here because
            # of the special logic to ensure writes are made to both tables.
            ClickHouseTable.VARIANTS_MEMORY: direct_insert_annotations,
            ClickHouseTable.KEY_LOOKUP: functools.partial(
                direct_insert_all_keys,
                clickhouse_table=self,
            ),
            ClickHouseTable.VARIANT_DETAILS: functools.partial(
                direct_insert_all_keys,
                clickhouse_table=self,
            ),
        }[self]

    @classmethod
    def for_dataset_type(cls, dataset_type: DatasetType) -> list['ClickHouseTable']:
        tables = [
            ClickHouseTable.VARIANTS_MEMORY,
            ClickHouseTable.KEY_LOOKUP,
        ]
        if dataset_type.should_write_new_variant_details:
            tables = [
                *tables,
                ClickHouseTable.VARIANT_DETAILS,
            ]
        return tables

    @classmethod
    def for_dataset_type_disk_backed_variants_tables(
        cls,
        _dataset_type: DatasetType,
    ) -> list['ClickHouseTable']:
        return [
            ClickHouseTable.VARIANTS_DISK,
        ]

    @classmethod
    def for_dataset_type_atomic_entries_update(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseTable']:
        return [
            *cls.for_dataset_type_atomic_entries_update_project_partitioned(
                dataset_type,
            ),
            *cls.for_dataset_type_atomic_entries_update_unpartitioned(dataset_type),
        ]

    @classmethod
    def for_dataset_type_atomic_entries_update_project_partitioned(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseTable']:
        if dataset_type == DatasetType.GCNV:
            return [ClickHouseTable.ENTRIES]
        return [
            ClickHouseTable.ENTRIES,
            ClickHouseTable.PROJECT_GT_STATS,
        ]

    @classmethod
    def for_dataset_type_atomic_entries_update_unpartitioned(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseTable']:
        if dataset_type == DatasetType.GCNV:
            return []
        return [ClickHouseTable.GT_STATS]


class ClickHouseDictionary(StrEnum):
    GT_STATS_DICT = 'gt_stats_dict'

    @classmethod
    def for_dataset_type(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseDictionary']:
        if dataset_type == DatasetType.GCNV:
            return []
        return list(cls)


class ClickHouseMaterializedView(StrEnum):
    ENTRIES_TO_PROJECT_GT_STATS_MV = 'entries_to_project_gt_stats_mv'
    PROJECT_GT_STATS_TO_GT_STATS_MV = 'project_gt_stats_to_gt_stats_mv'

    @classmethod
    def for_dataset_type_atomic_entries_update(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseMaterializedView']:
        if dataset_type == DatasetType.GCNV:
            return []
        return [
            ClickHouseMaterializedView.ENTRIES_TO_PROJECT_GT_STATS_MV,
            ClickHouseMaterializedView.PROJECT_GT_STATS_TO_GT_STATS_MV,
        ]

    @classmethod
    def for_dataset_type_atomic_entries_update_refreshable(
        cls,
        dataset_type: DatasetType,
    ) -> list['ClickHouseMaterializedView']:
        if dataset_type == DatasetType.GCNV:
            return []
        return [ClickHouseMaterializedView.PROJECT_GT_STATS_TO_GT_STATS_MV]


ClickHouseEntity = ClickHouseDictionary | ClickHouseTable | ClickHouseMaterializedView


@dataclass
class TableNameBuilder:
    reference_genome: ReferenceGenome
    dataset_type: DatasetType
    run_id: str

    @property
    def run_id_hash(self):
        # Note: encountered length issues with the default
        # run ids generated by the pipeline.  ClickHouse performed
        # well with staging Tables with the long run ids, but failed
        # to recognized staging Dictionaries.
        sha256 = hashlib.sha256()
        sha256.update(self.run_id.encode())
        return sha256.hexdigest()[:8]

    @property
    def dst_prefix(self):
        return f'{Env.CLICKHOUSE_DATABASE}.`{self.reference_genome.value}/{self.dataset_type.value}'

    def dst_table(self, clickhouse_entity: ClickHouseEntity):
        return f'{self.dst_prefix}/{clickhouse_entity.value}`'

    @property
    def staging_dst_prefix(self):
        return f'{STAGING_CLICKHOUSE_DATABASE}.`{self.run_id_hash}/{self.reference_genome.value}/{self.dataset_type.value}'

    def staging_dst_table(self, clickhouse_table: ClickHouseTable):
        return f'{self.staging_dst_prefix}/{clickhouse_table.value}`'

    def src_table(self, clickhouse_table: ClickHouseTable):
        path = os.path.join(
            clickhouse_table.src_path_fn(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
            '*.parquet',
        )
        if path.startswith('gs://'):
            return f"gcs({GCS_NAMED_COLLECTION}, url='{path.replace('gs://', GOOGLE_XML_API_PATH)}')"
        return f"file('{path}', 'Parquet')"


class ClickhouseReferenceDataset(StrEnum):
    ABSPLICE2 = 'absplice2'
    CLINVAR = 'clinvar'
    DBNSFP = 'dbnsfp'
    EIGEN = 'eigen'
    GNOMAD_EXOMES = 'gnomad_exomes'
    GNOMAD_GENOMES = 'gnomad_genomes'
    GNOMAD_MITO = 'gnomad_mito'
    GNOMAD_MITO_HETEROPLASMY = 'gnomad_mito_heteroplasmy'
    GNOMAD_NON_CODING_CONSTRAINT = 'gnomad_non_coding_constraint'
    HELIX_MITO = 'helix_mito'
    HELIX_MITO_HETEROPLASMY = 'helix_mito_heteroplasmy'
    HGMD = 'hgmd'
    HMTVAR = 'hmtvar'
    LOCAL_CONSTRAINT_MITO = 'local_constraint_mito'
    MITIMPACT = 'mitimpact'
    MITOMAP = 'mitomap'
    PEXT = 'pext'
    PROMOTER_AI = 'promoterAI'
    SCREEN = 'screen'
    SPLICE_AI = 'splice_ai'
    TOPMED = 'topmed'

    @property
    def all_variants_mv_timeout(self):
        return {
            ClickhouseReferenceDataset.DBNSFP: WAIT_VIEW_TIMEOUT_S * 3,
            ClickhouseReferenceDataset.SPLICE_AI: WAIT_VIEW_TIMEOUT_S * 10,
        }.get(self, WAIT_VIEW_TIMEOUT_S)

    @property
    def fully_refreshable(self):
        return self != ClickhouseReferenceDataset.CLINVAR

    @property
    def has_seqr_variants(self):
        return self not in {
            ClickhouseReferenceDataset.GNOMAD_NON_CODING_CONSTRAINT,
            ClickhouseReferenceDataset.SCREEN,
        }

    @classmethod
    def for_reference_genome_dataset_type(
        cls,
        reference_genome: ReferenceGenome,
        dataset_type: DatasetType,
    ):
        if dataset_type in {DatasetType.SV, DatasetType.GCNV}:
            return []
        return {
            (ReferenceGenome.GRCh38, DatasetType.MITO): [
                ClickhouseReferenceDataset.CLINVAR,
                ClickhouseReferenceDataset.DBNSFP,
                ClickhouseReferenceDataset.GNOMAD_MITO,
                ClickhouseReferenceDataset.GNOMAD_MITO_HETEROPLASMY,
                ClickhouseReferenceDataset.HELIX_MITO,
                ClickhouseReferenceDataset.HELIX_MITO_HETEROPLASMY,
                ClickhouseReferenceDataset.HMTVAR,
                ClickhouseReferenceDataset.LOCAL_CONSTRAINT_MITO,
                ClickhouseReferenceDataset.MITIMPACT,
                ClickhouseReferenceDataset.MITOMAP,
                ClickhouseReferenceDataset.PEXT,
            ],
            (ReferenceGenome.GRCh37, DatasetType.SNV_INDEL): [
                ClickhouseReferenceDataset.CLINVAR,
                ClickhouseReferenceDataset.DBNSFP,
                ClickhouseReferenceDataset.EIGEN,
                ClickhouseReferenceDataset.GNOMAD_EXOMES,
                ClickhouseReferenceDataset.GNOMAD_GENOMES,
                ClickhouseReferenceDataset.HGMD,
                ClickhouseReferenceDataset.SPLICE_AI,
                ClickhouseReferenceDataset.TOPMED,
            ],
            (ReferenceGenome.GRCh38, DatasetType.SNV_INDEL): [
                ClickhouseReferenceDataset.ABSPLICE2,
                ClickhouseReferenceDataset.CLINVAR,
                ClickhouseReferenceDataset.DBNSFP,
                ClickhouseReferenceDataset.EIGEN,
                ClickhouseReferenceDataset.GNOMAD_EXOMES,
                ClickhouseReferenceDataset.GNOMAD_GENOMES,
                ClickhouseReferenceDataset.GNOMAD_NON_CODING_CONSTRAINT,
                ClickhouseReferenceDataset.HGMD,
                ClickhouseReferenceDataset.PEXT,
                ClickhouseReferenceDataset.PROMOTER_AI,
                ClickhouseReferenceDataset.SCREEN,
                ClickhouseReferenceDataset.SPLICE_AI,
                ClickhouseReferenceDataset.TOPMED,
            ],
        }[(reference_genome, dataset_type)]

    @property
    def search_is_join_table(self):
        return self in {
            ClickhouseReferenceDataset.CLINVAR,
            ClickhouseReferenceDataset.HGMD,
        }

    def all_variants_path(self, table_name_builder: TableNameBuilder) -> str:
        return (
            f'{table_name_builder.dst_prefix}/reference_data/{self.value}/all_variants`'
        )

    def seqr_variants_path(self, table_name_builder: TableNameBuilder) -> str:
        return f'{table_name_builder.dst_prefix}/reference_data/{self.value}/seqr_variants`'

    def search_path(self, table_name_builder: TableNameBuilder) -> str:
        return f'{table_name_builder.dst_prefix}/reference_data/{self.value}`'

    def all_variants_mv(
        self,
        table_name_builder: TableNameBuilder,
    ) -> str:
        return f'{table_name_builder.dst_prefix}/reference_data/{self.value}/all_variants_mv`'

    def all_variants_to_seqr_variants_mv(
        self,
        table_name_builder: TableNameBuilder,
    ) -> str:
        return f'{table_name_builder.dst_prefix}/reference_data/{self.value}/all_variants_to_seqr_variants_mv`'

    def seqr_variants_to_search_mv_path(
        self,
        table_name_builder: TableNameBuilder,
    ) -> str:
        return f'{table_name_builder.dst_prefix}/reference_data/{self.value}/seqr_variants_to_search_mv`'

    def refresh_search(
        self,
        table_name_builder: TableNameBuilder,
    ) -> str:
        if self.search_is_join_table:
            logged_query(
                f"""
                SYSTEM START VIEW {self.seqr_variants_to_search_mv_path(table_name_builder)}
                """,
            )
            logged_query(
                f"""
                SYSTEM REFRESH VIEW {self.seqr_variants_to_search_mv_path(table_name_builder)}
                """,
            )
            logged_query(
                f"""
                SYSTEM WAIT VIEW {self.seqr_variants_to_search_mv_path(table_name_builder)}
                """,
                timeout=WAIT_VIEW_TIMEOUT_S,
            )
        else:
            logged_query(
                f"""
                SYSTEM RELOAD DICTIONARY {self.search_path(table_name_builder)}
                """,
            )

    def insert_into_seqr_variants_and_refresh_search(
        self,
        table_name_builder: TableNameBuilder,
    ):
        if not self.has_seqr_variants:
            return
        exists_seqr_variants = logged_query(
            f'EXISTS TABLE {self.seqr_variants_path(table_name_builder)}',
        )[0][0]
        if not exists_seqr_variants:
            return
        drop_staging_db()
        logged_query(
            f"""
            CREATE DATABASE {STAGING_CLICKHOUSE_DATABASE}
            """,
        )
        logged_query(
            f"""
            CREATE TABLE {table_name_builder.staging_dst_prefix}/_tmp_loadable_variantIds` ENGINE = Set AS (
                SELECT {ClickHouseTable.KEY_LOOKUP.key_field}
                FROM {table_name_builder.src_table(ClickHouseTable.KEY_LOOKUP)}
            )
            """,  # nosec B608
        )
        logged_query(
            f"""
            INSERT INTO {self.seqr_variants_path(table_name_builder)}
            SELECT
                DISTINCT ON (key)
                dst.key,
                COLUMNS('.*') EXCEPT(version, variantId, key)
            FROM {self.all_variants_path(table_name_builder)} src
            INNER JOIN {table_name_builder.dst_table(ClickHouseTable.KEY_LOOKUP)} dst
            ON {ClickHouseTable.KEY_LOOKUP.join_condition}
            WHERE src.variantId IN {table_name_builder.staging_dst_prefix}/_tmp_loadable_variantIds`
            """,  # nosec B608
        )
        self.refresh_search(table_name_builder)

    def download_and_fully_refresh(
        self,
        table_name_builder: TableNameBuilder,
    ):
        logged_query(
            f"""
            SYSTEM START VIEW {self.all_variants_mv(table_name_builder)}
            """,
        )
        logged_query(
            f"""
            SYSTEM REFRESH VIEW {self.all_variants_mv(table_name_builder)}
            """,
        )
        logged_query(
            f"""
            SYSTEM WAIT VIEW {self.all_variants_mv(table_name_builder)}
            """,
            timeout=self.all_variants_mv_timeout,
        )
        if self.has_seqr_variants:
            logged_query(
                f"""
                SYSTEM START VIEW {self.all_variants_to_seqr_variants_mv(table_name_builder)}
                """,
            )
            logged_query(
                f"""
                SYSTEM REFRESH VIEW {self.all_variants_to_seqr_variants_mv(table_name_builder)}
                """,
            )
            logged_query(
                f"""
                SYSTEM WAIT VIEW {self.all_variants_to_seqr_variants_mv(table_name_builder)}
                """,
                timeout=self.all_variants_mv_timeout,
            )
        self.refresh_search(table_name_builder)


def logged_query(query, params=None, timeout: int | None = None):
    client = get_clickhouse_client(timeout)
    sanitized_query = query
    if Env.CLICKHOUSE_WRITER_PASSWORD:
        sanitized_query = sanitized_query.replace(
            Env.CLICKHOUSE_WRITER_PASSWORD,
            REDACTED,
        )
    logger.info(f'Executing query: {sanitized_query} | Params: {params}')
    return client.execute(query, params)


def drop_staging_db():
    logged_query(f'DROP DATABASE IF EXISTS {STAGING_CLICKHOUSE_DATABASE};')


def create_staging_tables(
    table_name_builder: TableNameBuilder,
    clickhouse_tables: list[ClickHouseTable],
) -> None:
    logged_query(
        f"""
        CREATE DATABASE {STAGING_CLICKHOUSE_DATABASE}
        """,
    )
    for clickhouse_table in clickhouse_tables:
        logged_query(
            f"""
            CREATE
            TABLE {table_name_builder.staging_dst_table(clickhouse_table)}
            AS {table_name_builder.dst_table(clickhouse_table)}
            """,
        )


def get_create_mv_statements(
    table_name_builder: TableNameBuilder,
    clickhouse_mv: ClickHouseMaterializedView,
) -> tuple[str, str]:
    return logged_query(
        """
        SELECT create_table_query, as_select FROM system.tables
        WHERE
        engine = 'MaterializedView'
        AND database = %(database)s
        AND name = %(name)s
        """,
        {
            'database': Env.CLICKHOUSE_DATABASE,
            'name': table_name_builder.dst_table(clickhouse_mv)
            .split('.')[1]
            .replace('`', ''),
        },
    )[0]


def normalize_partition(partition: str) -> tuple:
    """
    Ensure a ClickHouse partition expression is always returned as a tuple.
    'project_d'       -> ('project_d',)
    "('project_d', 0)" -> ('project_d', 0)
    """
    if not isinstance(partition, str):
        msg = f'Unsupported partition type: {type(partition)}'
        raise TypeError(msg)
    partition = partition.strip()
    if partition.startswith('(') and partition.endswith(')'):
        return ast.literal_eval(partition)
    return (partition,)


def get_partitions_for_projects(
    table_name_builder: TableNameBuilder,
    clickhouse_table: ClickHouseTable,
    project_guids: list[str],
    staging=False,
):
    rows = logged_query(
        """
        SELECT DISTINCT partition
        FROM system.parts
        WHERE
            database = %(database)s
            AND table = %(table)s
            AND multiSearchAny(partition, %(project_guids)s)
        """,
        {
            'database': STAGING_CLICKHOUSE_DATABASE
            if staging
            else Env.CLICKHOUSE_DATABASE,
            'table': (
                table_name_builder.staging_dst_table(clickhouse_table)
                if staging
                else table_name_builder.dst_table(clickhouse_table)
            )
            .split('.')[1]
            .replace('`', ''),
            'project_guids': project_guids,
        },
    )
    return [normalize_partition(row[0]) for row in rows]


def create_staging_materialized_views(
    table_name_builder: TableNameBuilder,
    clickhouse_mvs: list[ClickHouseMaterializedView],
    mv_overrides: dict[ClickHouseMaterializedView, list[list[str]]] | None = None,
):
    for clickhouse_mv in clickhouse_mvs:
        create_table_statement = get_create_mv_statements(
            table_name_builder,
            clickhouse_mv,
        )[0]
        create_table_statement = create_table_statement.replace(
            table_name_builder.dst_prefix,
            table_name_builder.staging_dst_prefix,
        )
        for override in (mv_overrides or {}).get(clickhouse_mv, []):
            create_table_statement = create_table_statement.replace(*override)
        logged_query(create_table_statement)


# Note that this function is NOT idemptotent.  Clickhouse permits
# attaching the same partition to a table multiple times.
def stage_existing_project_partitions(
    table_name_builder: TableNameBuilder,
    project_guids: list[str],
    clickhouse_tables: list[ClickHouseTable],
):
    for clickhouse_table in clickhouse_tables:
        # Very important piece here:
        # ALL projects in the project_gt_stats table are staged, allowing us to rebuild
        # a production-quality gt_stats materialized view in the staging environment.
        if clickhouse_table == ClickHouseTable.PROJECT_GT_STATS:
            logged_query(
                f"""
                ALTER TABLE {table_name_builder.staging_dst_table(clickhouse_table)}
                ATTACH PARTITION ALL FROM {table_name_builder.dst_table(clickhouse_table)}
                """,
            )
            continue
        for partition in get_partitions_for_projects(
            table_name_builder,
            clickhouse_table,
            project_guids,
        ):
            # Note that ClickHouse successfully handles the case where the project
            # does not already exist in the dst table.  We simply attach an empty partition!
            logged_query(
                f"""
                ALTER TABLE {table_name_builder.staging_dst_table(clickhouse_table)}
                ATTACH PARTITION %(partition)s FROM {table_name_builder.dst_table(clickhouse_table)}
                """,
                {'partition': partition},
            )


def delete_existing_families_from_staging_entries(
    table_name_builder: TableNameBuilder,
    family_guids: list[str],
) -> None:
    logged_query(
        f"""
        INSERT INTO {table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)}
        SELECT COLUMNS('.*') EXCEPT(sign, n_partitions, partition_id), -1 as sign
        FROM {table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)}
        WHERE family_guid in %(family_guids)s
        """,  # nosec B608
        {'family_guids': family_guids},
    )


def insert_new_entries(
    table_name_builder: TableNameBuilder,
) -> None:
    dst_cols = [
        r[0]
        for r in logged_query(
            f'DESCRIBE TABLE {table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)}',
        )
    ]
    src_cols = [
        r[0]
        for r in logged_query(
            f'DESCRIBE TABLE {table_name_builder.src_table(ClickHouseTable.ENTRIES)}',
        )
    ]
    common, overrides = [c for c in dst_cols if c in src_cols], {}
    if 'geneId_ids' in dst_cols and 'geneIds' in src_cols:
        common = [c for c in common if c not in ('geneId_ids', 'geneIds')]
        common.append('geneId_ids')
        overrides['geneId_ids'] = f"""
            arrayFilter(
                x -> x IS NOT NULL,
                arrayMap(
                    g -> dictGetOrNull(
                        {Env.CLICKHOUSE_DATABASE}.`seqrdb_gene_ids`,
                        'seqrdb_id',
                        g
                    ),
                    geneIds
                )
            )
        """

    if (
        'is_gnomad_gt_5_percent' in dst_cols
        and 'is_gnomad_gt_5_percent' not in src_cols
    ):
        common.append('is_gnomad_gt_5_percent')
        overrides['is_gnomad_gt_5_percent'] = f"""
            dictGetOrDefault({ClickhouseReferenceDataset.GNOMAD_GENOMES.search_path(table_name_builder)}, 'filter_af', key, 0) > 0.05
        """

    dst_list = ', '.join(common)
    src_list = ', '.join([overrides.get(c, c) for c in common])
    logged_query(
        f"""
        INSERT INTO {table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)} ({dst_list})
        SELECT {src_list}
        FROM {table_name_builder.src_table(ClickHouseTable.ENTRIES)}
        """,  # nosec B608
    )


@retry(tries=2)
def optimize_entries(
    table_name_builder: TableNameBuilder,
    project_guids: list[str],
) -> None:
    max_attempts = 10
    for attempt in range(max_attempts):
        decrs_exist = logged_query(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM {table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)}
                WHERE sign = -1
            );
            """,  # nosec B608
        )[0][0]

        merges_running = logged_query(
            """
            SELECT EXISTS (
                SELECT 1
                FROM system.merges
                WHERE database = %(database)s
                AND table = %(table)s
            );
            """,
            {
                'database': STAGING_CLICKHOUSE_DATABASE,
                'table': table_name_builder.staging_dst_table(ClickHouseTable.ENTRIES)
                .split('.')[1]
                .replace('`', ''),
            },
        )[0][0]

        if not decrs_exist:
            return

        if merges_running:
            logger.info(
                'Decrs exist and merges are running, so waiting (attempt %d/%d)',
                attempt + 1,
                max_attempts,
            )
        else:
            logger.info(
                'Decrs exist and no merges are running, so optimizing (attempt %d/%d)',
                attempt + 1,
                max_attempts,
            )

            partitions = get_partitions_for_projects(
                table_name_builder,
                ClickHouseTable.ENTRIES,
                project_guids,
                staging=True,
            )
            table_name = table_name_builder.staging_dst_table(
                ClickHouseTable.ENTRIES,
            )
            optimize_statements = [
                f'OPTIMIZE TABLE {table_name} PARTITION {partition} FINAL'
                for partition in partitions
            ]
            parallel_optimize_sql = '\nPARALLEL WITH\n'.join(optimize_statements)

            logged_query(
                parallel_optimize_sql,
                timeout=OPTIMIZE_TABLE_TIMEOUT_S,
            )

        time.sleep(Env.CLICKHOUSE_OPTIMIZE_TABLE_WAIT_S)
    msg = f'Entries table still contains decrement rows after {max_attempts} attempts.'
    raise TimeoutError(msg)


@retry(tries=2)
def refresh_materialized_views(
    table_name_builder,
    materialized_views: list[ClickHouseMaterializedView],
    staging=False,
):
    for materialized_view in materialized_views:
        logged_query(
            f"""
            SYSTEM START VIEW {table_name_builder.staging_dst_table(materialized_view) if staging else table_name_builder.dst_table(materialized_view)}
            """,
        )
        logged_query(
            f"""
            SYSTEM REFRESH VIEW {table_name_builder.staging_dst_table(materialized_view) if staging else table_name_builder.dst_table(materialized_view)}
            """,
        )
        logged_query(
            f"""
            SYSTEM WAIT VIEW {table_name_builder.staging_dst_table(materialized_view) if staging else table_name_builder.dst_table(materialized_view)}
            """,
            timeout=WAIT_VIEW_TIMEOUT_S,
        )


def validate_family_guid_counts(
    table_name_builder: TableNameBuilder,
    project_guids: list[str],
    family_guids: list[str],
) -> None:
    query = Template(
        """
        SELECT family_guid, COUNT(*)
        FROM $table_name
        WHERE project_guid in %(project_guids)s
        AND family_guid in %(family_guids)s
        GROUP BY 1
        """,
    )
    src_family_counts = dict(
        logged_query(
            query.substitute(
                table_name=table_name_builder.src_table(
                    ClickHouseTable.ENTRIES,
                ),
            ),
            {'family_guids': family_guids, 'project_guids': project_guids},
        ),
    )
    dst_family_counts = dict(
        logged_query(
            query.substitute(
                table_name=table_name_builder.staging_dst_table(
                    ClickHouseTable.ENTRIES,
                ),
            ),
            {'family_guids': family_guids, 'project_guids': project_guids},
        ),
    )
    if src_family_counts != dst_family_counts:
        msg = 'Loaded Row counts are different than expected.'
        raise ValueError(msg)


@retry(tries=2)
def reload_dictionaries(
    table_name_builder: TableNameBuilder,
    dictionaries: list[ClickHouseDictionary],
):
    for dictionary in dictionaries:
        logged_query(
            f"""
            SYSTEM RELOAD DICTIONARY {table_name_builder.dst_table(dictionary)}
            """,  # nosec B608
        )


def replace_project_partitions(
    table_name_builder: TableNameBuilder,
    clickhouse_tables: list[ClickHouseTable],
    project_guids: list[str],
) -> None:
    for clickhouse_table in clickhouse_tables:
        for partition in get_partitions_for_projects(
            table_name_builder,
            clickhouse_table,
            project_guids,
            staging=True,
        ):
            logged_query(
                f"""
                ALTER TABLE {table_name_builder.dst_table(clickhouse_table)}
                REPLACE PARTITION %(partition)s FROM {table_name_builder.staging_dst_table(clickhouse_table)}
                """,  # nosec B608
                {'partition': partition},
            )


# Note this is NOT idempotent, as running the swap twice will
# result in the tables not being swapped.
def exchange_tables(
    table_name_builder,
    clickhouse_tables: list[ClickHouseTable],
) -> None:
    for clickhouse_table in clickhouse_tables:
        logged_query(
            f"""
            EXCHANGE TABLES {table_name_builder.staging_dst_table(clickhouse_table)} AND {table_name_builder.dst_table(clickhouse_table)}
            """,  # nosec B608
        )


def direct_insert_annotations(
    table_name_builder: TableNameBuilder,
    **_,
) -> None:
    dst_table = table_name_builder.dst_table(ClickHouseTable.VARIANTS_MEMORY)
    src_table = table_name_builder.src_table(ClickHouseTable.VARIANTS_MEMORY)
    drop_staging_db()
    logged_query(
        f"""
        CREATE DATABASE {STAGING_CLICKHOUSE_DATABASE}
        """,  # nosec B608
    )
    # NB: Unfortunately there's a bug(?) or inaccuracy if this is attempted without an intermediate
    # temporary table, likely due to writing to a table and joining against it at the same time.
    logged_query(
        f"""
        CREATE TABLE {table_name_builder.staging_dst_prefix}/_tmp_loadable_keys` ENGINE = Set AS (
            SELECT {ClickHouseTable.VARIANTS_MEMORY.key_field}
            FROM {src_table} src
            LEFT ANTI JOIN {dst_table} dst
            ON {ClickHouseTable.VARIANTS_MEMORY.join_condition}
        )
        """,  # nosec B608
    )
    for (
        clickhouse_table
    ) in ClickHouseTable.for_dataset_type_disk_backed_variants_tables(
        table_name_builder.dataset_type,
    ):
        disk_backed_dst_table = table_name_builder.dst_table(clickhouse_table)
        disk_backed_src_table = table_name_builder.src_table(clickhouse_table)
        logged_query(
            f"""
            INSERT INTO {disk_backed_dst_table}
            SELECT {clickhouse_table.select_fields}
            FROM {disk_backed_src_table} WHERE {clickhouse_table.key_field} IN {table_name_builder.staging_dst_prefix}/_tmp_loadable_keys`
            """,  # nosec B608
        )
    logged_query(
        f"""
        INSERT INTO {dst_table}
        SELECT {ClickHouseTable.VARIANTS_MEMORY.select_fields}
        FROM {src_table} WHERE {ClickHouseTable.VARIANTS_MEMORY.key_field} IN {table_name_builder.staging_dst_prefix}/_tmp_loadable_keys`
        """,  # nosec B608
    )
    drop_staging_db()


def direct_insert_all_keys(
    clickhouse_table: ClickHouseTable,
    table_name_builder: TableNameBuilder,
    **_,
) -> None:
    dst_table = table_name_builder.dst_table(clickhouse_table)
    src_table = table_name_builder.src_table(clickhouse_table)
    settings = ''
    # Large variant details inserts may OOM
    if clickhouse_table == ClickHouseTable.VARIANT_DETAILS:
        settings = 'SETTINGS max_insert_threads = 2'
    logged_query(
        f"""
        INSERT INTO {dst_table}
        SELECT {clickhouse_table.select_fields}
        FROM {src_table}
        {settings}
        """,  # nosec B608
    )


def export_existing_variants_to_parquet(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
    export_select_fields: str,
) -> None:
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    variants_table = table_name_builder.dst_table(
        ClickHouseTable.VARIANT_DETAILS
        if dataset_type.should_write_new_variant_details
        else ClickHouseTable.VARIANTS_MEMORY,
    )
    export_table = table_name_builder.src_table(
        ClickHouseTable.EXISTING_VARIANTS,
    ).replace(
        '/*.parquet',
        '',
    )
    logged_query(
        f"""
        INSERT INTO FUNCTION {export_table}
        SELECT {export_select_fields}
        FROM {variants_table}
        """,  # nosec B608
    )


# This is a smattering of shared operations that lacks a better name :/
def finalize_refresh_flow(
    table_name_builder: TableNameBuilder,
    project_guids: list[str],
):
    dataset_type = table_name_builder.dataset_type
    refresh_materialized_views(
        table_name_builder,
        ClickHouseMaterializedView.for_dataset_type_atomic_entries_update_refreshable(
            dataset_type,
        ),
        staging=True,
    )
    replace_project_partitions(
        table_name_builder,
        ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
            dataset_type,
        ),
        project_guids,
    )
    exchange_tables(
        table_name_builder,
        ClickHouseTable.for_dataset_type_atomic_entries_update_unpartitioned(
            dataset_type,
        ),
    )
    drop_staging_db()
    reload_dictionaries(
        table_name_builder,
        ClickHouseDictionary.for_dataset_type(dataset_type),
    )


def atomic_insert_entries(
    table_name_builder: TableNameBuilder,
    project_guids: list[str],
    family_guids: list[str],
    **_,
) -> None:
    dataset_type = table_name_builder.dataset_type
    drop_staging_db()
    create_staging_tables(
        table_name_builder,
        ClickHouseTable.for_dataset_type_atomic_entries_update(dataset_type),
    )

    mv_overrides = None
    ordered_mv_table = None
    if dataset_type == DatasetType.SNV_INDEL:
        # Create a copy of the PROJECT_GT_STATS table ordered by key for the GT_STATS materialized view source
        # This allows clickhouse to utilize a memory optimized group by only available for sorted tables
        table_suffix = 'key_ordered'
        base_table = table_name_builder.staging_dst_table(ClickHouseTable.PROJECT_GT_STATS)
        ordered_mv_table = f'{base_table}/{table_suffix}'
        logged_query(f'CREATE TABLE {ordered_mv_table} AS {base_table} ORDER BY key')
        mv_overrides = {
            ClickHouseMaterializedView.PROJECT_GT_STATS_TO_GT_STATS_MV: [
                [base_table, ordered_mv_table],
                [';', ' SETTINGS max_memory_usage=10000000000, max_bytes_before_external_group_by=5000000000, optimize_aggregation_in_order=1;'],
            ],
        }

    create_staging_materialized_views(
        table_name_builder,
        ClickHouseMaterializedView.for_dataset_type_atomic_entries_update(
            dataset_type,
        ),
        mv_overrides=mv_overrides,
    )
    stage_existing_project_partitions(
        table_name_builder,
        project_guids,
        ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
            dataset_type,
        ),
    )
    delete_existing_families_from_staging_entries(
        table_name_builder,
        family_guids,
    )
    insert_new_entries(
        table_name_builder,
    )
    optimize_entries(
        table_name_builder,
        project_guids,
    )
    validate_family_guid_counts(
        table_name_builder,
        project_guids,
        family_guids,
    )
    if ordered_mv_table:
        logged_query(
            f"""
            INSERT INTO {ordered_mv_table}
            SELECT(*)
            FROM {table_name_builder.staging_dst_table(ClickHouseTable.PROJECT_GT_STATS)}
            """,
        )
    finalize_refresh_flow(table_name_builder, project_guids)


@retry()
def load_run_variants(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
):
    msg = f'Attempting load of variants for run: {reference_genome.value}/{dataset_type.value}/{run_id}'
    logger.info(msg)
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    for clickhouse_table in ClickHouseTable.for_dataset_type(dataset_type):
        clickhouse_table.insert(
            table_name_builder=table_name_builder,
        )
    for (
        clickhouse_reference_data
    ) in ClickhouseReferenceDataset.for_reference_genome_dataset_type(
        reference_genome,
        dataset_type,
    ):
        clickhouse_reference_data.insert_into_seqr_variants_and_refresh_search(
            table_name_builder=table_name_builder,
        )


@retry()
def load_run_entries(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
    project_guids: list[str],
    family_guids: list[str],
):
    msg = f'Attempting load of entries for run: {reference_genome.value}/{dataset_type.value}/{run_id}'
    logger.info(msg)
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    atomic_insert_entries(
        table_name_builder=table_name_builder,
        project_guids=project_guids,
        family_guids=family_guids,
    )


@retry()
def delete_family_guids(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
    project_guid: str,
    family_guids: list[str],
):
    msg = f'Attempting delete families for {reference_genome.value}/{dataset_type.value} {project_guid}: {family_guids}'
    logger.info(msg)
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    entries_exist = logged_query(
        f"""
        SELECT EXISTS (
            SELECT 1
            FROM {table_name_builder.dst_table(ClickHouseTable.ENTRIES)}
            WHERE project_guid = %(project_guid)s
            AND has(%(family_guids)s, family_guid)
        );
        """,  # nosec B608
        {'family_guids': family_guids, 'project_guid': project_guid},
    )[0][0]
    if not entries_exist:
        msg = f'No data exists for {reference_genome.value} & {dataset_type.value} so skipping'
        logger.info(msg)
        return
    project_guids = [project_guid]
    drop_staging_db()
    create_staging_tables(
        table_name_builder,
        ClickHouseTable.for_dataset_type_atomic_entries_update(dataset_type),
    )
    create_staging_materialized_views(
        table_name_builder,
        ClickHouseMaterializedView.for_dataset_type_atomic_entries_update(
            dataset_type,
        ),
    )
    stage_existing_project_partitions(
        table_name_builder,
        project_guids,
        ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
            dataset_type,
        ),
    )
    delete_existing_families_from_staging_entries(
        table_name_builder,
        family_guids,
    )
    optimize_entries(
        table_name_builder,
        project_guids,
    )
    finalize_refresh_flow(table_name_builder, project_guids)


@retry()
def rebuild_gt_stats(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
    project_guids: list[str],
) -> None:
    if ClickHouseDictionary.GT_STATS_DICT not in ClickHouseDictionary.for_dataset_type(
        dataset_type,
    ):
        msg = f'Skipping gt stats rebuild for {reference_genome.value}/{dataset_type.value} {project_guids[:10]}...'
        logger.info(msg)
        return
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    max_key = logged_query(
        f"""
        SELECT max(key) FROM {table_name_builder.dst_table(ClickHouseTable.GT_STATS)}
        """,  # nosec B608
    )[0][0]
    if not max_key:
        msg = f'Skipping gt stats rebuild for empty dataset {reference_genome.value}/{dataset_type.value} {project_guids[:10]}...'
        logger.info(msg)
        return
    msg = f'Attempting rebuild gt stats for {reference_genome.value}/{dataset_type.value} {project_guids[:10]}...'
    logger.info(msg)
    drop_staging_db()
    create_staging_tables(
        table_name_builder,
        ClickHouseTable.for_dataset_type_atomic_entries_update(dataset_type),
    )
    create_staging_materialized_views(
        table_name_builder,
        ClickHouseMaterializedView.for_dataset_type_atomic_entries_update(
            dataset_type,
        ),
    )
    stage_existing_project_partitions(
        table_name_builder,
        project_guids,
        ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
            dataset_type,
        ),
    )
    for partition in get_partitions_for_projects(
        table_name_builder,
        ClickHouseTable.PROJECT_GT_STATS,
        project_guids,
        staging=True,
    ):
        logged_query(
            f"""
            ALTER TABLE {table_name_builder.staging_dst_table(ClickHouseTable.PROJECT_GT_STATS)}
            DROP PARTITION %(partition)s
            """,  # nosec B608
            {'partition': partition},
        )
    select_statement = get_create_mv_statements(
        table_name_builder,
        ClickHouseMaterializedView.ENTRIES_TO_PROJECT_GT_STATS_MV,
    )[1]
    select_statement = select_statement.replace(
        table_name_builder.dst_prefix,
        table_name_builder.staging_dst_prefix,
    )
    # NB: encountered OOMs with large projects, necessitating sharding the insertion query.
    step = math.ceil(max_key / 5)
    for range_start in range(0, max_key, step):
        range_end = min(range_start + step, max_key + 1)
        logged_query(
            f"""
            INSERT INTO {
                table_name_builder.staging_dst_table(ClickHouseTable.PROJECT_GT_STATS)
            }
            {
                select_statement.replace(
                    'GROUP BY project_guid',
                    'WHERE key >= %(range_start)s AND key < %(range_end)s GROUP BY project_guid',
                )
            }
            """,
            {'range_start': range_start, 'range_end': range_end},
        )
    finalize_refresh_flow(table_name_builder, project_guids)


@retry()
def refresh_clickhouse_reference_data(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
    reference_dataset: ClickhouseReferenceDataset,
):
    if not reference_dataset.fully_refreshable:
        msg = f'Skipping reference dataset refresh for {reference_dataset.value} for {reference_genome.value}/{dataset_type.value}..'
        logger.info(msg)
        return
    msg = f'Attempting refresh reference dataset {reference_dataset.value} for {reference_genome.value}/{dataset_type.value} ... '
    logger.info(msg)
    table_name_builder = TableNameBuilder(
        reference_genome,
        dataset_type,
        run_id,
    )
    reference_dataset.download_and_fully_refresh(table_name_builder)


def get_clickhouse_client(
    timeout: int | None = None,
    database: str | None = None,
) -> Client:
    return Client(
        host=Env.CLICKHOUSE_SERVICE_HOSTNAME,
        port=Env.CLICKHOUSE_SERVICE_PORT,
        user=Env.CLICKHOUSE_WRITER_USER,
        password=Env.CLICKHOUSE_WRITER_PASSWORD,
        **{'database': database} if database else {},
        **{'send_receive_timeout': timeout} if timeout else {},
        **{
            'settings': {
                'send_timeout': timeout,
                'receive_timeout': timeout,
            },
        }
        if timeout
        else {},
    )
