"""Stub of `seqr.utils.logging_utils` - see `seqr/__init__.py` in this stub package for why.

`SeqrLogger` is mirrored verbatim from the real `seqr/utils/logging_utils.py` (it's already
dependency-free: stdlib `logging` plus this app's own `settings.DEPLOYMENT_TYPE`). Only
`SeqrLogger` is reproduced, since it's the only symbol `clickhouse_search` actually imports from
this module (`clickhouse_search/backend/table_models.py`).
"""

import logging
from typing import Optional


class SeqrLogger(object):

    def __init__(self, name: Optional[str] = None) -> None:
        """Custom logger which requires user metadata to be included in the log."""
        self._logger = logging.getLogger(name)

    def _log(self, level, message, user, **kwargs):
        self._logger.log(level, message, extra=dict(user=user, **kwargs))

    def debug(self, *args, **kwargs):
        self._log(logging.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self._log(logging.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._log(logging.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self._log(logging.ERROR, *args, **kwargs)
