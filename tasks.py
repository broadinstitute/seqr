import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xbrowse_server.settings")

from xbrowse_server import xbrowse_controls

from celery import Celery
celery = Celery('tasks', backend='amqp', broker='amqp://')

@celery.task
def annotate_vcf(vcf_file, overwrite):
    xbrowse_controls.annotate_vcf(vcf_file, overwrite)

@celery.task
def re_run_vep(vcf_file): 
    xbrowse_controls.re_run_vep(vcf_file)


#
# New
#

@celery.task
def reload_project(project_id, annotate):
    xbrowse_controls.reload_project(project_id, annotate=annotate)

@celery.task
def reload_project_variants(project_id):
    xbrowse_controls.reload_project_coverage(project_id)
    xbrowse_controls.reload_project_variants(project_id)

@celery.task
def reload_family_variants(project_id, family_id):
    xbrowse_controls.reload_family_coverage(project_id, family_id)
    xbrowse_controls.reload_family_variants(project_id, family_id)

@celery.task
def reload_cohort_variants(project_id, cohort_id):
    xbrowse_controls.reload_cohort_variants(project_id, cohort_id)

@celery.task
def preload_vep_vcf_annotations(vcf_file_path):
    xbrowse_controls.preload_vep_vcf_annotations(vcf_file_path)