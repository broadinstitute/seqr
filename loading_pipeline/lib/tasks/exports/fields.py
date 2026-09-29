import hail as hl

from loading_pipeline.lib.annotations.shared import variant_id, xpos
from loading_pipeline.lib.core import DatasetType, SampleType


def get_entries_export_fields(
    ht: hl.Table,
    dataset_type: DatasetType,
    sample_type: SampleType,
):
    return {
        'project_guid': ht.family_entries.project_guid[0],
        'family_guid': ht.family_entries.family_guid[0],
        **(
            {
                'sample_type': sample_type.value,
                'variantId': variant_id(ht),
                'xpos': xpos(ht),
            }
            if dataset_type in {DatasetType.SNV_INDEL, DatasetType.MITO}
            else {'variantId': ht.variant_id}
        ),
        'filters': ht.filters,
        'calls': hl.sorted(ht.family_entries, key=lambda fe: fe.s).map(
            lambda fe: fe.rename({'s': 'sampleId'}).drop('family_guid', 'project_guid'),
        ),
        'sign': 1,
    }
