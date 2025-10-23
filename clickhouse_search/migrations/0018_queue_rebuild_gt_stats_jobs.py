# Generated manually by the seqr team
import math

from django.db import migrations
import requests

from settings import PIPELINE_RUNNER_SERVER


def batch_project_guids(project_guids, max_batches=30, min_batch_size=5):
    n = len(project_guids)
    if n == 0:
        return []
    batch_size = max(math.ceil(n / max_batches), min_batch_size)
    return [project_guids[i : i + batch_size] for i in range(0, n, batch_size)]


def queue_rebuild_gt_stats_jobs(apps, schema_editor):
    Project = apps.get_model("seqr", "Project")
    for batch in batch_project_guids(
        list(Project.objects.using("default").values_list("guid", flat=True))
    ):
        response = requests.post(
            f"{PIPELINE_RUNNER_SERVER}/rebuild_gt_stats_enqueue",
            json={"project_guids": batch},
            timeout=60,
        )
        response.raise_for_status()
        print(f"Triggered rebuild_gt_stats_enqueue for {batch}")


class Migration(migrations.Migration):
    dependencies = [
        ("clickhouse_search", "0017_fix_affected_status_column_order"),
    ]

    operations = [
        migrations.RunPython(queue_rebuild_gt_stats_jobs),
    ]
