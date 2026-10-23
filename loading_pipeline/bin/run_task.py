#!/usr/bin/env python3
import sys

import luigi

import loading_pipeline.lib.core  # noqa: F401 # pylint: disable=unused-import
from loading_pipeline.lib.tasks import *  # noqa: F403 # nosec F403

if __name__ == '__main__':
    # If run does not succeed, exit with 1 status code.
    luigi.run() or sys.exit(1)  # pylint: disable=W0106
