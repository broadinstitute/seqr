from collections import defaultdict

from django.core.management.base import BaseCommand

from seqr.models import Project, Family, VariantTag, VariantTagType, Sample
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.airflow_utils import trigger_airflow_delete_families, DagRunningException

import logging
logger = logging.getLogger(__name__)


def _disable_search(families, from_project):
    search_samples = Sample.objects.filter(is_active=True, individual__family__in=families)
    if search_samples:
        updated_families = search_samples.values_list("individual__family__family_id", flat=True).distinct()
        updated_family_dataset_types = list(search_samples.values_list('dataset_type', 'individual__family__guid').distinct())
        family_summary = ", ".join(sorted(updated_families))
        num_updated = search_samples.update(is_active=False)
        logger.info(
            f'Disabled search for {num_updated} samples in the following {len(updated_families)} families: {family_summary}'
        )
        _trigger_delete_families_dags(from_project, updated_family_dataset_types)

def _trigger_delete_families_dags(from_project, updated_family_dataset_types):
    updated_families_by_dataset_type = defaultdict(list)
    for dataset_type, family_guid in updated_family_dataset_types:
        updated_families_by_dataset_type[dataset_type].append(family_guid)

    for dataset_type, family_guids in sorted(updated_families_by_dataset_type.items()):
        try:
            trigger_airflow_delete_families(dataset_type, family_guids, from_project)
            logger.info(f'Successfully triggered DELETE_FAMILIES DAG for {len(family_guids)} {dataset_type} families')
        except Exception as e:
            logger_call = logger.warning if isinstance(e, DagRunningException) else logger.error
            logger_call(str(e))

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)
        parser.add_argument('family_ids', nargs='+')

    def handle(self, *args, **options):
        from_project = Project.objects.get(guid=options['from_project'])
        to_project = Project.objects.get(guid=options['to_project'])
        family_ids = options['family_ids']
        families = Family.objects.filter(project=from_project, family_id__in=family_ids)
        num_found = len(families)

        num_expected = len(set(family_ids))
        missing_id_message = '' if num_found == num_expected else f' No match for: {", ".join(set(family_ids) - set([f.family_id for f in families]))}.'
        logger.info(f'Found {num_found} out of {num_expected} families.{missing_id_message}')

        backend_specific_call(lambda *args: None, _disable_search)(families, from_project)

        for variant_tag_type in VariantTagType.objects.filter(project=from_project):
            variant_tags = VariantTag.objects.filter(saved_variants__family__in=families, variant_tag_type=variant_tag_type)
            if variant_tags:
                logger.info('Updating "{}" tags'.format(variant_tag_type.name))
                to_tag_type, created = VariantTagType.objects.get_or_create(
                    project=to_project, name=variant_tag_type.name
                )
                if created:
                    to_tag_type.category = variant_tag_type.category
                    to_tag_type.description = variant_tag_type.description
                    to_tag_type.color = variant_tag_type.color
                    to_tag_type.order = variant_tag_type.order
                    to_tag_type.save()
                variant_tags.update(variant_tag_type=to_tag_type)

        logger.info("Updating families")
        families.update(project=to_project)

        logger.info("Done.")
