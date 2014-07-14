from django.conf import settings
from xbrowse_server.base.models import ReferencePopulation
from xbrowse.annotation import PopulationFrequencyStore


_custom_population_store = None
def custom_population_store():
    global _custom_population_store
    if _custom_population_store is None:
        _custom_population_store = PopulationFrequencyStore(
            db_conn=settings.CUSTOM_POPULATIONS_DB,
            reference_populations=ReferencePopulation.get_annotator_spec()
        )
    return _custom_population_store