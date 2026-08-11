from string import Template

import hail as hl

from loading_pipeline.lib.core import DatasetType, Env, ReferenceGenome

VEP_CONFIG_URI = Template(
    'file://$vep_reference_datasets_dir/$reference_genome/vep-$reference_genome.json',
)


def run_vep(
    ht: hl.Table,
    dataset_type: DatasetType,
    reference_genome: ReferenceGenome,
) -> hl.Table:
    if not dataset_type.veppable:
        return ht
    return hl.vep(
        ht,
        config=VEP_CONFIG_URI.substitute(
            vep_reference_datasets_dir=Env.VEP_REFERENCE_DATASETS_DIR,
            reference_genome=reference_genome.value,
        ),
        name='vep',
        block_size=1000,
        tolerate_parse_error=True,
        csq=False,
    )
