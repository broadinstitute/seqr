import itertools
from dataclasses import dataclass, field
from enum import Enum

import hail as hl
import numpy as np

from loading_pipeline.lib.core import Sex

DEFAULT_RELATEDNESS_TOLERANCE = 0.2
PARENT_CHILD_RELATEDNESS_TOLERANCE = 0.4


class Relation(Enum):
    PARENT_CHILD = 'parent_child'
    GRANDPARENT_GRANDCHILD = 'grandparent_grandchild'
    SIBLING = 'sibling'
    HALF_SIBLING = 'half_sibling'
    AUNT_NEPHEW = 'aunt_nephew'

    @property
    def coefficients(self):
        return {
            Relation.PARENT_CHILD: [0, 1, 0, 0.5],
            Relation.GRANDPARENT_GRANDCHILD: [0.5, 0.5, 0, 0.25],
            Relation.SIBLING: [0.25, 0.5, 0.25, 0.5],
            Relation.HALF_SIBLING: [0.5, 0.5, 0, 0.25],
            Relation.AUNT_NEPHEW: [0.5, 0.5, 0, 0.25],
        }[self]

    def coefficients_equal(self, coefficients: list[float]) -> bool:
        if self == Relation.PARENT_CHILD:
            return np.allclose(
                coefficients[0],
                self.coefficients[0],
                atol=0.025,
            ) and np.allclose(
                coefficients[1:],
                self.coefficients[1:],
                atol=DEFAULT_RELATEDNESS_TOLERANCE,
            )
        return np.allclose(
            coefficients,
            self.coefficients,
            atol=DEFAULT_RELATEDNESS_TOLERANCE,
        )


@dataclass
class Sample:
    sample_id: str
    sex: Sex
    mother: str = None
    father: str = None
    maternal_grandmother: str = None
    maternal_grandfather: str = None
    paternal_grandmother: str = None
    paternal_grandfather: str = None
    siblings: list[str] = field(default_factory=list)
    half_siblings: list[str] = field(default_factory=list)
    aunt_nephews: list[str] = field(default_factory=list)

    def is_aunt_nephew(self: 'Sample', other: 'Sample') -> bool:
        return (
            # My Maternal Grandparents are your Parents
            self.maternal_grandmother
            and self.maternal_grandfather
            and (self.maternal_grandmother == other.mother)
            and (self.maternal_grandfather == other.father)
        ) or (
            # My Paternal Grandparents are your Parents
            self.paternal_grandmother
            and self.paternal_grandfather
            and (self.paternal_grandmother == other.mother)
            and (self.paternal_grandfather == other.father)
        )

    def is_in_direct_lineage(self: 'Sample', other: 'Sample') -> bool:
        return self.sample_id in {
            other.mother,
            other.father,
            other.maternal_grandmother,
            other.maternal_grandfather,
            other.paternal_grandmother,
            other.paternal_grandfather,
        } or other.sample_id in {
            self.mother,
            self.father,
            self.maternal_grandmother,
            self.maternal_grandfather,
            self.paternal_grandmother,
            self.paternal_grandfather,
        }


@dataclass
class Family:
    family_guid: str
    samples: dict[str, Sample]

    def __hash__(self):
        return hash(self.family_guid)

    def __eq__(self, other):
        return self.family_guid == other.family_guid

    @staticmethod
    def parse_direct_lineage(rows: list[hl.Struct]) -> dict[str, Sample]:
        samples = {}
        for row in rows:
            samples[row.s] = Sample(
                sample_id=row.s,
                sex=Sex(row.sex),
                mother=row.maternal_s,
                father=row.paternal_s,
            )

        for row in rows:
            # Maternal GrandParents
            maternal_s = samples[row.s].mother
            if maternal_s and maternal_s in samples:
                if samples[maternal_s].mother:
                    samples[row.s].maternal_grandmother = samples[maternal_s].mother
                if samples[maternal_s].father:
                    samples[row.s].maternal_grandfather = samples[maternal_s].father

            # Paternal GrandParents
            paternal_s = samples[row.s].father
            if paternal_s and paternal_s in samples:
                if samples[paternal_s].mother:
                    samples[row.s].paternal_grandmother = samples[paternal_s].mother
                if samples[paternal_s].father:
                    samples[row.s].paternal_grandfather = samples[paternal_s].father
        return samples

    @staticmethod
    def parse_collateral_lineage(
        samples: dict[str, Sample],
    ) -> dict[str, Sample]:
        # NB: relationships are identified unidirectionally here (for better or for worse)
        # A sample_i that is siblings with sample_j, will list sample_j as as sibling, but
        # sample_j will not list sample_i as a sibling.  Relationships only appear in the
        # ibd table a single time, so we only need to check the pairing once.
        for sample_i, sample_j in itertools.combinations(samples.values(), 2):
            # If sample is already related from direct relationships, continue
            if sample_i.is_in_direct_lineage(sample_j):
                continue

            # If both parents are identified and the same, samples are siblings.
            if (
                sample_i.mother
                and sample_i.father
                and (sample_i.mother == sample_j.mother)
                and (sample_i.father == sample_j.father)
            ):
                sample_i.siblings.append(sample_j.sample_id)
                continue

            # If only a single parent is identified and the same, samples are half siblings
            if (sample_i.mother and sample_i.mother == sample_j.mother) or (
                sample_i.father and sample_i.father == sample_j.father
            ):
                sample_i.half_siblings.append(sample_j.sample_id)
                continue

            # If either set of one's grandparents is identified and equal to the other's parents,
            # they're aunt/uncle related
            # NB: because we will only check an i, j pair of samples a single time, (itertools.combinations)
            # we need to check both grandparents_i == parents_j and parents_i == grandparents_j.
            if sample_i.is_aunt_nephew(sample_j) or sample_j.is_aunt_nephew(sample_i):
                sample_i.aunt_nephews.append(sample_j.sample_id)
        return samples

    @classmethod
    def parse(cls, family_guid: str, rows: list[hl.Struct]) -> 'Family':
        samples = cls.parse_direct_lineage(rows)
        samples = cls.parse_collateral_lineage(samples)
        return cls(
            family_guid=family_guid,
            samples=samples,
        )


def parse_pedigree_ht_to_families(
    pedigree_ht: hl.Table,
) -> set[Family]:
    families = set()
    for family_guid, rows in itertools.groupby(
        sorted(pedigree_ht.collect(), key=lambda x: x.family_guid),
        lambda x: x.family_guid,
    ):
        families.add(Family.parse(family_guid, list(rows)))
    return families


def parse_pedigree_ht_to_remap_ht(pedigree_ht: hl.Table) -> hl.Table:
    ht = pedigree_ht.filter(hl.is_defined(pedigree_ht.remap_id))
    ht = ht.annotate(seqr_id=ht.s)
    ht = ht.key_by(s=ht.remap_id)
    return ht.select('seqr_id')
