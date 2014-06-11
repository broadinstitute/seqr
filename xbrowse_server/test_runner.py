import pymongo

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

from xbrowse.mongo_datastore import MongoDatastore
from xbrowse.reference import Reference
from xbrowse import loader
from xbrowse import vcf_stuff

from xbrowse_controls import pull_project_from_datastore, create_project_from_datastore
from xbrowse_server.base.models import Project

class XBrowseServerTestRunner(DjangoTestSuiteRunner): 
    """
    Custom test runner for xbrowse-server.


    """

    def setup_test_environment(self, **kwargs):

        super(XBrowseServerTestRunner, self).setup_test_environment(**kwargs)

        pymongo.Connection().drop_database('xbrowse_test')
        settings.DATASTORE = MongoDatastore(db_name='xbrowse_test')
        settings.REFERENCE = Reference()

        # TODO: validate reference

        # add g1k_trios project
        loader.add_family_project(settings.DATASTORE, settings.REFERENCE, 'g1k_trios',
            settings.TEST_DATA_DIR + 'g1k_trios.fam', settings.G1K_ANNOTATED_VCF)

#
#        # add g1k_cohort project
#        cohort_samples = [s.strip() for s in open(settings.TEST_DATA_DIR + 'g1k_cohort.samples.txt').readlines()]
#        cohort = vcf_stuff.get_cohort_from_vcf('g1k_cohort', 'probands', , cohort_samples)
#        settings.DATASTORE.add_cohort(cohort)
#        settings.DATASTORE.assign_variant_files(cohort, vcf_file=vcf_file)
#
#        add_single_cohort_project('g1k_cohort', 'probands', settings.G1K_ANNOTATED_VCF, cohort_samples)