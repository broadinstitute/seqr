import hail as hl

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.reference_datasets.misc import vcf_to_ht


def get_ht(path: str, reference_genome: ReferenceGenome) -> hl.Table:
    ht = vcf_to_ht(path, reference_genome)
    ht = ht.select(
        KEY=ht.rsid,
        AF=ht.info.AF[0],
        AC=ht.info.AC[0],
        AN=ht.info.AN,
        N_HET=ht.info.N_HET,
        N_HOM=ht.info.N_HOMALT,
    )
    return ht.key_by('KEY')
