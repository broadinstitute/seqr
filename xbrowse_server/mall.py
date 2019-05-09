from django.conf import settings
from xbrowse.cnv import CNVStore
from xbrowse.coverage import CoverageDatastore
from xbrowse.datastore import MongoDatastore
from xbrowse.datastore.elasticsearch_datastore import ElasticsearchDatastore
from xbrowse.datastore.population_datastore import PopulationDatastore
from xbrowse.reference import Reference
from xbrowse.annotation import PopulationFrequencyStore, VariantAnnotator
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator


x_custom_populations = None
x_custom_populations_map = None


_custom_population_store = None
def get_custom_population_store():
    global _custom_population_store
    global x_custom_populations
    if _custom_population_store is None:
        if x_custom_populations is None:
            raise Exception('x_custom_populations has not been set yet')
        _custom_population_store = PopulationFrequencyStore(
            get_db=lambda: settings.CUSTOM_POPULATIONS_DB,
            reference_populations=x_custom_populations,
        )
    return _custom_population_store


_reference = None
def get_reference():
    global _reference
    if _reference is None:
        _reference = Reference(settings.REFERENCE_SETTINGS)
    return _reference


_custom_annotator = None
def get_custom_annotator():
    global _custom_annotator
    # custom annotator can be None
    if _custom_annotator is None and settings.CUSTOM_ANNOTATOR_SETTINGS:
        _custom_annotator = CustomAnnotator()

    return _custom_annotator


_annotator = None
def get_annotator():
    global _annotator
    if _annotator is None:
        _annotator = VariantAnnotator(
            custom_annotator=get_custom_annotator(),
        )
    return _annotator

_mongo_datastore = None
_elasticsearch_datastore = None
def get_datastore(project=None):
    global _mongo_datastore
    global _elasticsearch_datastore
    global x_custom_populations_map

    if project.get_elasticsearch_index() is None:
        if _mongo_datastore is None:
            if x_custom_populations_map is None:
                raise Exception('x_custom_populations_map has not been set yet')
            _mongo_datastore = MongoDatastore(
                'DATASTORE_DB',
                get_annotator(),
                get_custom_population_store(),
                x_custom_populations_map,
            )
        return _mongo_datastore
    else:
        if _elasticsearch_datastore is None:
            _elasticsearch_datastore = ElasticsearchDatastore(get_annotator())
        return _elasticsearch_datastore


_population_datastore = None
def get_population_datastore():
    global _population_datastore
    if _population_datastore is None:
        _population_datastore = PopulationDatastore(
            'POPULATION_DATASTORE_DB',
            get_annotator(),
            get_custom_population_store(),
            settings.CONTROL_COHORTS,
        )
    return _population_datastore


_coverage_store = None
def get_coverage_store():
    global _coverage_store
    if _coverage_store is None:
        _coverage_store = CoverageDatastore(settings.COVERAGE_DB, get_reference())
    return _coverage_store


_project_mongo_datastore = None
_project_elasticsearch_datastore = None
def get_mongo_project_datastore():
    global _project_mongo_datastore

    if _project_mongo_datastore is None:
        if x_custom_populations_map is None:
            raise Exception('x_custom_populations_map has not been set yet')
        _project_mongo_datastore = MongoDatastore(
            'PROJECT_DATASTORE_DB',
            get_annotator(),
            get_custom_population_store(),
            x_custom_populations_map,
        )

    return _project_mongo_datastore


def get_project_datastore(project=None):
    global _project_mongo_datastore
    global _elasticsearch_datastore  # same datastore can be used for project and family searches
    global x_custom_populations_map

    if project.has_elasticsearch_index():
        if _elasticsearch_datastore is None:
            _elasticsearch_datastore = ElasticsearchDatastore(get_annotator())
        return _elasticsearch_datastore
    else:
        return get_mongo_project_datastore()


_cnv_store = None
def get_cnv_store():
    global _cnv_store
    if _cnv_store is None:
        _cnv_store = CNVStore(settings.CNV_STORE_DB_NAME, get_reference())
    return _cnv_store


class Mall():
    """
    A mall contains lots of stores
    """
    def __init__(
            self,
            reference=None,
            annotator=None,
            variant_store=None,
            cnv_store=None,
            custom_population_store=None,
            coverage_store=None,
        ):
        self.reference = reference
        self.annotator = annotator
        self.variant_store = variant_store
        self.cnv_store = cnv_store
        self.custom_population_store = custom_population_store
        self.coverage_store = coverage_store


def get_mall(project=None):
    # do not cache Mall because it depends on the project arg
    _mall = Mall(
        reference=get_reference(),
        annotator=get_annotator(),
        variant_store=get_datastore(project),
        cnv_store=get_cnv_store(),
        custom_population_store=get_custom_population_store(),
        coverage_store=get_coverage_store(),
    )
    return _mall
