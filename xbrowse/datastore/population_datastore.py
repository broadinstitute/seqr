from xbrowse.datastore import MongoDatastore
from xbrowse import Individual, Cohort

class PopulationDatastore(MongoDatastore):

    # TODO: return cohort obj
    def get_control_cohort(self, population):
        indiv_id_list = self.get_individuals_for_family(population, 'control_cohort')
        individuals = [Individual(indiv_id, affected_status='affected') for indiv_id in indiv_id_list]
        cohort = Cohort('control_cohort', individuals, project_id=population)
        return cohort

    def get_control_cohort_size(self, population):
        return len(self.get_individuals_for_family(population, 'control_cohort'))