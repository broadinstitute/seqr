from django.apps import AppConfig
from xbrowse_server import mall


class XBrowseBaseConfig(AppConfig):

    name = 'xbrowse_server.base'

    def ready(self):
        """
        This is an additional initialization step after all of the django models are instantiated.
        Some of the Stores in the Mall depend on data stored in the db.
        For example, the Datastore (ie. VariantStore) needs to know which projects have access to
        which custom reference populations.
        We set that up here, rather than store the state in the Datastore itself, to reduce the complexity of the Datastore API.
        """
        Project = self.get_model('Project')
        mall.x_custom_populations_map = {p.project_id: p.private_reference_population_slugs() for p in Project.objects.all()}

        ReferencePopulation = self.get_model('ReferencePopulation')
        mall.x_custom_populations = [p.to_dict() for p in ReferencePopulation.objects.all()]
