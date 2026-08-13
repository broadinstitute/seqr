# No-op stand-in for the real seqr app's migration of the same name.
#
# `clickhouse_search`'s migration `0040_gnomadnoncodingconstraintdict.py` declares a cross-app
# migration dependency on exactly this (app_label, name) pair, purely for historical
# migration-ordering reasons - not because it touches any table this migration would create.
# Django's migration graph builder requires a *named* dependency (unlike `__first__`/`__latest__`)
# to exist as a real node in the graph even for an otherwise-unmigrated app, so this file exists
# solely to satisfy that graph edge. See `seqr/__init__.py` in this stub package for more context.
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = []
