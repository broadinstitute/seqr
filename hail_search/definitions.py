from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, DefaultDict, Set


class SampleType(Enum):
    WES = 'WES'
    WGS = 'WGS'

@dataclass
class Sample:
    individual_guid: str
    family_guid: str
    project_guid: str
    affected: str
    sample_id: str

@dataclass
class SampleData:
    samples: List[Sample] = field(default_factory=list)  # | bool


@dataclass
class FamilyData:
    sample_data: Dict[SampleType, SampleData] = field(default_factory=dict)

    def get_sample_types(self) -> Set[SampleType]:
        return set(self.sample_data.keys())


@dataclass
class ProjectData:
    family_data: Dict[str, FamilyData] = field(default_factory=dict)

    def get_first_family(self) -> Tuple[str, FamilyData]:
        return next(iter(self.family_data.items()))

    def get_sample_types_for_all_families(self) -> Set[SampleType]:
        return {
            sample_type
            for family_data in self.family_data.values()
            for sample_type in family_data.get_sample_types()
        }

@dataclass
class ProjectSamples:
    projects: Dict[str, ProjectData] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectSamples':
        projects = {}
        for project_guid, families_dict in data.items():
            family_data_dict = {}
            for family_guid, sample_types_dict in families_dict.items():
                sample_data_dict = {
                    sample_type: SampleData(samples)
                    for sample_type, samples in sample_types_dict.items()
                }
                family_data_dict[family_guid] = FamilyData(sample_data_dict)
            projects[project_guid] = ProjectData(family_data_dict)

        return cls(projects)

    def get_first_project(self) -> Tuple[str, ProjectData]:
        return next(iter(self.projects.items()))
