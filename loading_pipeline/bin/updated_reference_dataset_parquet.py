#!/usr/bin/env python3
import argparse

import luigi

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.reference_data.updated_reference_dataset_parquet import (
    UpdatedReferenceDatasetParquetOnDataprocTask,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference-genome', required=True, type=ReferenceGenome)
    parser.add_argument('--dataset-type', required=True, type=DatasetType)
    parser.add_argument(
        '--reference-dataset',
        required=True,
        type=ReferenceDataset,
    )
    args = parser.parse_args()
    luigi.build(
        [
            UpdatedReferenceDatasetParquetOnDataprocTask(
                reference_genome=args.reference_genome,
                dataset_type=args.dataset_type,
                reference_dataset=args.reference_dataset,
                run_id=f'{args.reference_dataset.value.replace("_", "-").lower()}-run',
                attempt_id=0,
            ),
        ],
    )


if __name__ == '__main__':
    main()
