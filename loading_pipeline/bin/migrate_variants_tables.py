#!/usr/bin/env python3
import argparse
import uuid

import luigi

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.core.constants import VARIANTS_MIGRATION_RUN_ID
from loading_pipeline.lib.tasks.variants_migration.load_clickhouse_variants_tables import (
    LoadClickhouseVariantsTablesTask,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run variants migration Luigi pipeline.',
    )
    parser.add_argument(
        '--run_all_dataset_types',
        action='store_true',
        help='If set, runs the pipeline for all dataset types instead of just SNV_INDEL.',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    for reference_genome, dataset_type in [
        (ReferenceGenome.GRCh37, DatasetType.SNV_INDEL),
        (ReferenceGenome.GRCh38, DatasetType.SNV_INDEL),
        (ReferenceGenome.GRCh38, DatasetType.MITO),
        (ReferenceGenome.GRCh38, DatasetType.SV),
        (ReferenceGenome.GRCh38, DatasetType.GCNV),
    ]:
        if dataset_type != DatasetType.SNV_INDEL and not args.run_all_dataset_types:
            continue
        run_id_prefix = (
            VARIANTS_MIGRATION_RUN_ID + '-' + str(uuid.uuid1().int)[:4]
        )  # Note: the randomness is a cache bust for the luigi local scheduler
        luigi.build(
            [
                LoadClickhouseVariantsTablesTask(
                    reference_genome,
                    dataset_type,
                    run_id=run_id_prefix,
                    attempt_id=0,
                ),
            ],
        )
