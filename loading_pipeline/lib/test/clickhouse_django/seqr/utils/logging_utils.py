# Mirrors the real seqr.utils.logging_utils.SeqrLogger (dependency-free) - see seqr/__init__.py.
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
