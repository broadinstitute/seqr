from enum import Enum


class SampleType(str, Enum):
    WES = 'WES'
    WGS = 'WGS'

    @property
    def family_entries_field(self) -> str:
        return {
            SampleType.WES: 'wes_family_entries',
            SampleType.WGS: 'wgs_family_entries',
        }[self]

    @property
    def failed_family_sample_field(self) -> str:
        return {
            SampleType.WES: f'wes_failed_family_sample_indices',
            SampleType.WGS: f'wgs_failed_family_sample_indices',
        }[self]

    @property
    def passes_inheritance_field(self) -> str:
        return {
            SampleType.WES: 'wes_passes_inheritance',
            SampleType.WGS: 'wgs_passes_inheritance',
        }[self]

    @property
    def passes_quality_field(self) -> str:
        return {
            SampleType.WES: 'wes_passes_quality',
            SampleType.WGS: 'wgs_passes_quality',
        }[self]

    @property
    def other_sample_type(self) -> 'SampleType':
        return {
            SampleType.WES: SampleType.WGS,
            SampleType.WGS: SampleType.WES,
        }[self]
