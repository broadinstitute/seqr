import os
import shutil

from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.paths import valid_reference_dataset_path
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

REFERENCE_DATASETS_PATH = 'loading_pipeline/var/test/reference_datasets'


class MockedReferenceDatasetsTestCase(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        for reference_genome in ReferenceGenome:
            path = os.path.join(
                REFERENCE_DATASETS_PATH,
                reference_genome.value,
            )
            # Use listdir, allowing for missing datasets
            # in the tests.
            for dataset_name in os.listdir(
                path,
            ):
                # Copy the entire directory tree under
                # the dataset name.
                shutil.copytree(
                    os.path.join(path, dataset_name),
                    os.path.dirname(
                        valid_reference_dataset_path(
                            reference_genome,
                            ReferenceDataset(dataset_name),
                        ),
                    ),
                )

    def tearDown(self):
        super().tearDown()
