import re

import luigi

from loading_pipeline.lib.core import Env, ReferenceGenome
from loading_pipeline.lib.core.constants import (
    MIGRATION_RUN_ID,
    VARIANTS_MIGRATION_RUN_ID,
)

CLUSTER_NAME_PREFIX = 'pipeline-runner'


def get_cluster_name(reference_genome: ReferenceGenome, run_id: str):
    if MIGRATION_RUN_ID in run_id:
        return f'{Env.DEPLOYMENT_TYPE}-{CLUSTER_NAME_PREFIX}-{reference_genome.value.lower()}-hs-to-clckhse-mgrtn'
    if VARIANTS_MIGRATION_RUN_ID in run_id:
        return f'{Env.DEPLOYMENT_TYPE}-{CLUSTER_NAME_PREFIX}-{reference_genome.value.lower()}-vrnts-mgrtn'
    return f'{Env.DEPLOYMENT_TYPE}-{CLUSTER_NAME_PREFIX}-{reference_genome.value.lower()}-{run_id}'


def snake_to_kebab_arg(snake_string: str) -> str:
    return '--' + re.sub(r'\_', '-', snake_string).lower()


def to_kebab_str_args(task: luigi.Task):
    return [
        e for k, v in task.to_str_params().items() for e in (snake_to_kebab_arg(k), v)
    ]
