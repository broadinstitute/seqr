import os
import pymongo
import imp


# django stuff
xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
xbrowse_reference_data_dir = os.path.join(xbrowse_install_dir, 'data/reference_data')

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
URL_PREFIX = '/'

GENERATED_FILES_DIR = os.path.join(os.path.dirname(__file__), 'generated_files')

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(xbrowse_install_dir, 'xbrowse_db.sqlite'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'xbrowsedb',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


#
# xbrowse stuff
#


SLACK_TOKEN = 'xoxp-2258598853-12795159268-112897781589-3f697c4d5ac4cf2efd7ea8fcebe750c0'

PROJECTS_WITH_MATCHMAKER = [
    'pierce_retinal-degeneration_cmg-samples_exomes_v1',
    'manton_orphan-diseases_cmg-samples_exomes_v1',
    'guptill_exomes_v1',
    'estonian_external_exomes',
    'INMR_v9',
    'gleeson_cmg-samples_exomes_v1',
    'CMG_Hildebrandt_Exomes',
    'CMG_Hildebrandt_Exomes_External',
    'Anne-External-Exome',
]


MME_PATIENT_PRIMARY_DATA_OWNER = {
    'manton_orphan-diseases_cmg-samples_exomes_v1':'Pankaj Agrawal',
    'estonian_external_exomes':'Katrin Ounap',
    'gleeson_cmg-samples_exomes_v1' : 'Joe Gleeson',
    'CMG_VCGS_Exomes' : 'Sue White',
    'guptill_exomes_v1': 'Jeffery Guptill',
    'pierce_retinal-degeneration_cmg-samples_exomes_v1':'Eric Pierce',
    'INMR_v9':  'Sandra Cooper',
    'CMG_Hildebrandt_Exomes_External':'Hildebrandt, Friedhelm',
    'CMG_Hildebrandt_Exomes':'Hildebrandt, Friedhelm',
    'Anne-External-Exome': "O'Donnell, Anne",
}




PROJECTS_WITHOUT_PHENOTIPS = {
    'RNA-seq-BC',
    'temp2_Henrickson_Skin_11S', 
    'PID21192-VQSR-merck', 
    'IBD_Exomes_May2016', 
    
    'Amel-1S',
    'Amel-Sims-40S',
    'AnnPoduri-4Prj-140S',
    'AnnPoduri-C1809',
    'AnnPoduri-ChildrenHospital',
    'AnnPoduri-RP-633',
    'BC-149BP_RNA',
    'BC-S47-RNA',
    'BCH-Trio-49S',
    'Bonnemann-14-49S',
    'Bonnemann-16-3S',
    'Bonnemann-17-29S',
    'Bonnemann-Int92-Ext123S',
    'Bonnemann-Jan2016-107S',
    'Bonnemann-WGS-Batch3',
    'Bonnemann_PCRFree_WGS_v2',
    'Bonnemann_WGS_batch4',
    'CDH-89S',
    'CDH2-292S',
    'DS-Trio-140485-Broad',
    'DS-Trio-140485-GeneDx',
    'Dowling_v10',
    'EV-Udler',
    'Fabian-MP-10S',
    'HICMP-JW-5S',
    'Harlands-11S',
    'Harlands-F1',
    'IBD-Sokol-18S',
    'IBD-Trio-For-RG',
    'IBD_273_Samples',
    'INMR_PCRFree_WGS_v4',
    'Jueppner_3S_PCRfree_WGS',
    'Laing_PCRFree_WGS_v2',
    'Lin-Cohort-2S',
    'MODY-250S',
    'MYOSEQ_v15',
    'MYOSEQ_v16',
    'Manton-PCRfree-4S',
    'Marneros-Acc-16S',
    'Merck-Annotation-WE',
    'Merck-Phase5-WGS-CCHMC',
    'Merck-Phase5-WGS-NIAMS',
    'Merck-extVCF-S208-WE',
    'Merck-extVCF-S208-WGS',
    'Merck_Phase5_WGS_NIAID',
    'MitoExome271',
    'Muntoni_PCRFree_WGS_v4',
    'MyoSeq_v8',
    'NCL-51S',
    'PID21192-merck',
    'Purpura_Fulminans-2S',
    'Qatar-WGS-9S',
    'RR-CANVAS-20S',
    'Sample-1413-1',
    'Sarah_Beecroft_IonTorrent_D13',
    'Seddon-WE-9newS',
    'Thorburn100-mitoexome2',
    'Thorburn100.mitoexome2-2',
    'UNC-3S',
    'Udler-Acromegaly-WES',
    'VEO-IBD-549S',
    'VEO-IBD-579S',
    'WHT-Ann-15S',
    'Weastmead-WGS-3S',
    'Winters-ExEx-S17',
    'bonnemann',
    'bonnemann_v9',
    'cohen_merck_wgs',
    'cotsapas_RE_exomes-42S',
    'eo-ibd-mgh',
    'family_T_somatic_analysis_B2asTumor',
    'family_T_somatic_analysis_F1asTumor',
    'hanson_merck_wgs',
    'inmr',
    'jkb',
    'meei_pierce',
    'merck_insomnia',
    'milner_merck_wgs',
    'muscle_wgs',
    'myoseq_v11',
    'myoseq_v12',
    'newcastle_v9',
    'niaid_merck_wgs',
    'niams_merck_wgs',
    'pgcs',
    'pgcs-case31',
    'snapper_merck_wgs',
    'walter_v13'
}


REFERENCE_SETTINGS = imp.load_source(
    'reference_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/reference_settings.py'
)

CUSTOM_ANNOTATOR_SETTINGS = imp.load_source(
    'custom_annotation_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/custom_annotator_settings.py'
)

ANNOTATOR_SETTINGS = imp.load_source(
    'annotator_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/annotator_settings.py'
)

_conn = pymongo.MongoClient()
DATASTORE_DB = _conn['xbrowse_datastore']
POPULATION_DATASTORE_DB = _conn['xbrowse_pop_datastore']

DEFAULT_CONTROL_COHORT = 'controls'
CONTROL_COHORTS = [
    {
        'slug': 'controls',
        'vcf': '',
    },
]

COVERAGE_DB = _conn['xbrowse_coverage']

PROJECT_DATASTORE_DB = _conn['xbrowse_proj_store']

CNV_STORE_DB_NAME = 'xbrowse_cnvs'

CUSTOM_POPULATIONS_DB = _conn['xcustom_refpops']

READ_VIZ_BAM_PATH = os.path.join(xbrowse_reference_data_dir, "bams")

CLINVAR_TSV  = os.path.join(xbrowse_reference_data_dir, "clinvar.tsv")


MEDIA_ROOT = os.path.abspath(GENERATED_FILES_DIR + "/media/")


# Email settings
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
