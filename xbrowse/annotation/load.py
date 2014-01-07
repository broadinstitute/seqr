from population_frequency_store import PopulationFrequencyStore


def create_population_frequency_store_from_settings(db, settings_module):
    """
    Creates a population frequency store from scratch.
    Args:
        db: empty pymongo Database
        settings_module: module with REFERENCE_POPULATIONS setting
    """
    store = PopulationFrequencyStore(db)
    store.ensure_indices()
    store.load_populations(settings_module.REFERENCE_POPULATIONS)
