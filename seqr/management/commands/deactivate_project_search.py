from django.core.management.base import BaseCommand, CommandError

from seqr.models import Project, Sample
from seqr.views.utils.airflow_utils import is_airflow_enabled, trigger_airflow_dag, DELETE_PROJECTS_DAG_NAME

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project')

    def handle(self, *args, **options):
        project = Project.objects.get(guid=options['project'])

        if input(f'Are you sure you want to deactivate search for {project.name} (y/n)? ') != 'y':
            raise CommandError('Error: user did not confirm')

        updated = Sample.bulk_update(user=None, update_json={'is_active': False}, individual__family__project=project)

        logger.info(f'Deactivated {len(updated)} samples')

        if updated and is_airflow_enabled():
            dataset_types = Sample.objects.filter(guid__in=updated).values_list('dataset_type', flat=True).distinct()
            for dataset_type in dataset_types:
                trigger_airflow_dag(DELETE_PROJECTS_DAG_NAME, project, 'SNV_INDEL')
                logger.info(f'Successfully triggered {DELETE_PROJECTS_DAG_NAME} DAG for {dataset_type} {project.guid}')
