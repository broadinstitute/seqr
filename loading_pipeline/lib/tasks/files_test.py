import os
import tempfile
import unittest

from loading_pipeline.lib.tasks.files import (
    CallsetTask,
    HailTableTask,
    RawFileTask,
    VCFFileTask,
)


class FilesTest(unittest.TestCase):
    def test_raw_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            self.assertTrue(RawFileTask(f.name).complete())

    def test_vcf_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix='.vcf.bgz') as f:
            self.assertTrue(VCFFileTask(f.name).complete())

    def test_hail_table(self) -> None:
        with tempfile.TemporaryDirectory(suffix='.ht') as d:
            self.assertFalse(HailTableTask(d).complete())
            with open(os.path.join(d, '_SUCCESS'), 'w') as f:
                f.write('0')
            self.assertTrue(HailTableTask(d).complete())

    def test_callset_task(self) -> None:
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            self.assertTrue(CallsetTask(f.name).complete())

        with tempfile.NamedTemporaryFile(suffix='.vcf') as f:
            self.assertTrue(CallsetTask(f.name).complete())

        with tempfile.TemporaryDirectory(suffix='.mt') as d:
            self.assertFalse(CallsetTask(d).complete())
            with open(os.path.join(d, '_SUCCESS'), 'w') as f:
                f.write('0')
            self.assertTrue(CallsetTask(d).complete())
