from django.core.management.base import BaseCommand
import logging
from elasticsearch_dsl import Index

from seqr.utils.es_utils import get_es_client, get_latest_loaded_samples
from seqr.models import Project

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        client = get_es_client()
        indices = [index['index'] for index in client.cat.indices(format="json", h='index')
                   if index['index'] not in ['.kibana', 'index_operations_log']]
        mappings = Index('_all', using=client).get_mapping(doc_type='variant')
        new_search_indices = {index_name for index_name in indices
                              if 'samples_num_alt_1' in mappings[index_name]['mappings']['variant']['properties']}

        latest_loaded_samples = get_latest_loaded_samples()
        project_ids_with_new_search = set()
        for sample in latest_loaded_samples:
            for index_name in sample.elasticsearch_index.split(','):
                if index_name in new_search_indices:
                    project_ids_with_new_search.add(sample.individual.family.project_id)
        Project.objects.filter(id__in=project_ids_with_new_search).update(has_new_search=True)
        logger.info('Set new search enabled for {} projects'.format(len(project_ids_with_new_search)))