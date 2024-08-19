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
class Family:
    samples_by_type: Dict[SampleType, List[Sample] | bool] = field(default_factory=dict)

    def get_sample_types(self) -> Set[SampleType]:
        return set(self.samples_by_type.keys())


@dataclass
class Project:
    families: Dict[str, Family] = field(default_factory=dict)

    def get_one_family(self) -> Tuple[str, Family]:
        return next(iter(self.families.items()))

    def get_sample_types_for_all_families(self) -> Set[SampleType]:
        return {
            sample_type
            for family in self.families.values()
            for sample_type in family.get_sample_types()
        }

@dataclass
class Projects:
    projects: Dict[str, Project] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'Projects':
        projects = {}
        for project_guid, families_dict in data.items():
            family_data_dict = {}
            for family_guid, sample_types_dict in families_dict.items():
                sample_data_dict = {
                    SampleType(sample_type): [Sample(**s) for s in samples]
                    for sample_type, samples in sample_types_dict.items()
                }
                family_data_dict[family_guid] = Family(sample_data_dict)
            projects[project_guid] = Project(family_data_dict)

        return cls(projects)

    @classmethod
    def from_lookup_dict(cls, data: dict) ->  'Projects':
        projects = {}
        for project_guid, project_data in data.items():
            family_data_dict = {}
            for family_guid, sample_types_dict in project_data.items():
                sample_data_dict = {
                    SampleType(sample_type): value
                    for sample_type, value in sample_types_dict.items()
                }
                family_data_dict[family_guid] = Family(sample_data_dict)
            projects[project_guid] = Project(family_data_dict)

        return cls(projects)


    def get_projects(self) -> Set[Tuple[str, Project]]:
        return set(self.projects.items())

    def get_one_project(self) -> Tuple[str, Project]:
        return next(iter(self.projects.items()))

    def get_sample_types_for_all_projects(self) -> Set[SampleType]:
        return {
            sample_type
            for project in self.projects.values()
            for sample_type in project.get_sample_types_for_all_families()
        }
