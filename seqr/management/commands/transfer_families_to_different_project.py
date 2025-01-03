from collections import defaultdict

from django.core.management.base import BaseCommand

from seqr.models import Project, Family, VariantTag, VariantTagType, Sample
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.airflow_utils import trigger_airflow_delete_families

import logging

from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)


SAMPLE_TYPE_WES = 'WES'
SAMPLE_TYPE_WGS = 'WGS'


def _disable_search(families):
    search_samples = Sample.objects.filter(is_active=True, individual__family__in=families)
    if search_samples:
        updated_families = search_samples.values_list("individual__family__family_id", flat=True).distinct()
        updated_family_dataset_types = list(search_samples.values_list('dataset_type', 'individual__family__family_id').distinct())
        family_summary = ", ".join(sorted(updated_families))
        num_updated = search_samples.update(is_active=False)
        logger.info(
            f'Disabled search for {num_updated} samples in the following {len(updated_families)} families: {family_summary}'
        )
        return updated_family_dataset_types


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

        updated_family_dataset_types = backend_specific_call(lambda f: None, _disable_search)(families)

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

        if updated_family_dataset_types:
            self.trigger_delete_families_dags(from_project, updated_family_dataset_types)

        logger.info("Updating families")
        families.update(project=to_project)
        logger.info("Done.")

    @staticmethod
    def trigger_delete_families_dags(from_project, updated_family_dataset_types):
        updated_families_by_dataset_type = defaultdict(list)
        for dataset_type, family_id in updated_family_dataset_types:
            updated_families_by_dataset_type[dataset_type].append(family_id)

        for dataset_type, family_ids in updated_families_by_dataset_type.items():
            families = Family.objects.filter(project=from_project, family_id__in=family_ids)
            success_message = f'Successfully deleted {len(families)} from {from_project.name} {dataset_type}'
            error_message = f'ERROR triggering delete families from {from_project.name} {dataset_type}'

            trigger_airflow_delete_families(
                dataset_type=dataset_type,
                genome_version=from_project.genome_version,
                error_message=error_message,
                families=families,
                projects=[from_project],
                success_message=success_message,
                success_slack_channel=SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL,
            )
