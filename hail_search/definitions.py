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
