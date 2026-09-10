from enum import StrEnum

import hail as hl


class Sex(StrEnum):
    FEMALE = 'F'
    MALE = 'M'
    UNKNOWN = 'U'
    XXX = 'XXX'
    X0 = 'X0'
    XXY = 'XXY'
    XYY = 'XYY'

    @property
    def imputed_sex_values(self) -> list[str]:
        return {
            Sex.MALE: ['Male'],
            Sex.FEMALE: ['Female'],
            Sex.UNKNOWN: ['', 'Unknown'],
        }.get(self, [self.name])


class ReferenceGenome(StrEnum):
    GRCh37 = 'GRCh37'
    GRCh38 = 'GRCh38'

    @property
    def v02_value(self) -> str:
        return self.value[-2:]

    @property
    def hl_reference(self) -> hl.ReferenceGenome:
        return hl.get_reference(self.value)

    @property
    def standard_contigs(self) -> set[str]:
        return {
            *self.hl_reference.contigs[:25],
        }

    @property
    def optional_contigs(self) -> set[str]:
        return {
            ReferenceGenome.GRCh37: {
                'Y',
                'MT',
            },
            ReferenceGenome.GRCh38: {
                'chrY',
                'chrM',
            },
        }[self]

    @property
    def mito_contig(self) -> str:
        return {
            ReferenceGenome.GRCh37: 'MT',
            ReferenceGenome.GRCh38: 'chrM',
        }[self]

    @property
    def x_contig(self) -> str:
        return 'X' if self == ReferenceGenome.GRCh37 else 'chrX'

    def contig_recoding(self, include_mt: bool = False) -> dict[str, str]:
        recode = {
            ReferenceGenome.GRCh37: {
                f'chr{i}': f'{i}' for i in ([*list(range(1, 23)), 'X', 'Y'])
            },
            ReferenceGenome.GRCh38: {
                f'{i}': f'chr{i}' for i in ([*list(range(1, 23)), 'X', 'Y'])
            },
        }[self]

        if include_mt and self == ReferenceGenome.GRCh38:
            recode.update({'MT': 'chrM'})
        if include_mt and self == ReferenceGenome.GRCh37:
            recode.update({'chrM': 'MT'})

        return recode


class SampleType(StrEnum):
    WES = 'WES'
    WGS = 'WGS'
