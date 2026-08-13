"""Stub of the main app's `seqr` package, shadowing it on sys.path (see settings.py's docstring).

`clickhouse_search`'s migrations need `SeqrLogger` (utils/logging_utils.py) and a specific `seqr`
migration name to exist, but not the real app - which imports guardian/postgres/social_django via
seqr/models.py. This stub avoids that weight.
"""
