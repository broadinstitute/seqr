import clickhouse_backend.models
import clickhouse_search.backend.engines
import clickhouse_search.backend.fields
from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0012_delete_annotationsdiskgcnv_and_more'),
    ]

    operations = [
    ]
