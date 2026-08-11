import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from loading_pipeline.lib.core import Env


class MockedDatarootTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        patcher = patch(
            'loading_pipeline.lib.paths.Env',
            wraps=Env,
        )  # wraps to ensure other attributes behave as they are.
        self.mock_env = patcher.start()
        self.addCleanup(patcher.stop)  # https://stackoverflow.com/a/37534051
        for field_name in Env.__dataclass_fields__:
            if field_name.endswith('_DIR'):
                setattr(self.mock_env, field_name, tempfile.TemporaryDirectory().name)

    def tearDown(self) -> None:
        super().tearDown()
        for field_name in Env.__dataclass_fields__:
            if os.path.isdir(getattr(self.mock_env, field_name)):
                shutil.rmtree(getattr(self.mock_env, field_name))
