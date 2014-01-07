from collections import OrderedDict

GENDERS = (
    'male',
    'female',
    'unknown'
)

AFFECTED_STATUSES = (
    'affected',
    'unaffected',
    'unknown'
)


class Individual():

    def __init__(self, indiv_id, **kwargs):
        self.indiv_id = indiv_id
        self.project_id = kwargs.get('project_id', '.')
        self.family_id = kwargs.get('family_id', '.')
        self.paternal_id = kwargs.get('paternal_id', '.')
        self.maternal_id = kwargs.get('maternal_id', '.')
        self.gender = kwargs.get('gender', '.')
        self.affected_status = kwargs.get('affected_status', '.')

    def toJSON(self):
        return {
            'indiv_id': self.indiv_id,
            'project_id': self.project_id,
            'family_id': self.family_id,
            'paternal_id': self.paternal_id,
            'maternal_id': self.maternal_id,
            'gender': self.gender,
            'affected_status': self.affected_status,
        }


class Family():

    def __init__(self, family_id, individuals, **kwargs):
        self.family_id = family_id
        self.project_id = kwargs.get('project_id', '.')

        indiv_ids = [i.indiv_id for i in individuals]
        if len(indiv_ids) != len(set(indiv_ids)):
            raise Exception('Individual IDs are not unique')
        self.individuals = {indiv.indiv_id: indiv for indiv in individuals}

    def toJSON(self):
        return {
            'family_id': self.family_id,
            'project_id': self.project_id,
            'individuals': {indiv.indiv_id: indiv.toJSON() for indiv in self.individuals.values()}
        }

    def indiv_id_list(self):
        return self.individuals.keys()

    def contains_indiv_id(self, indiv_id):
        return indiv_id in self.individuals

    def num_individuals(self):
        return len(self.individuals)

    def get_individuals(self):
        return self.individuals.values()

    def get_individual(self, indiv_id):
        return self.individuals.get(indiv_id)

    def get_affecteds(self):
        return [i for i in self.get_individuals() if i.affected_status == 'affected']

    def affected_status_map(self):
        return {indiv.indiv_id: indiv.affected_status for indiv in self.get_individuals()}


class Cohort():

    def __init__(self, cohort_id, individuals, **kwargs):
        self.cohort_id = cohort_id
        self.project_id = kwargs.get('project_id', '.')

        indiv_ids = [i.indiv_id for i in individuals]
        if len(indiv_ids) != len(set(indiv_ids)):
            raise Exception('Individual IDs are not unique')
        self.individuals = {indiv.indiv_id: indiv for indiv in individuals}

    def toJSON(self):
        return {
            'cohort_id': self.cohort_id,
            'project_id': self.project_id,
            'individuals': {indiv.indiv_id: indiv.toJSON() for indiv in self.individuals.values()}
        }

    def indiv_id_list(self):
        return self.individuals.keys()

    def contains_indiv_id(self, indiv_id):
        return indiv_id in self.individuals

    def get_individual(self, indiv_id):
        return self.individuals.get(indiv_id)


class FamilyGroup():

    def __init__(self, families, **kwargs):
        families = [((family.project_id, family.family_id), family) for family in families]
        self.families = OrderedDict(sorted(families, key=lambda t: t[0]))

    def toJSON(self):
        return [family.toJSON() for family in self.get_families()]

    def get_families(self):
        return self.families.values()