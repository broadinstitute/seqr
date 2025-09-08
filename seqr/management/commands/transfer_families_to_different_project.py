from django.core.management.base import BaseCommand

from clickhouse_search.search import delete_clickhouse_family
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample
from seqr.utils.search.utils import backend_specific_call

import logging
logger = logging.getLogger(__name__)


def _disable_search(families, from_project):
    search_samples = Sample.objects.filter(is_active=True, individual__family__in=families)
    if search_samples:
        updated_families = search_samples.values_list("individual__family__family_id", flat=True).distinct()
        updated_family_dataset_types = list(search_samples.values_list('individual__family__guid', 'dataset_type', 'sample_type').distinct())
        family_summary = ", ".join(sorted(updated_families))
        num_updated = search_samples.update(is_active=False)
        logger.info(
            f'Disabled search for {num_updated} samples in the following {len(updated_families)} families: {family_summary}'
        )
        for update in updated_family_dataset_types:
            logger.info(delete_clickhouse_family(from_project, *update))


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

        found_families = families
        families = families.filter(analysisgroup__isnull=True)
        if len(families) < num_found:
            update_family_ids = set([f.family_id for f in families])
            group_families = [
                f'{f.family_id} ({", ".join(f.analysisgroup_set.values_list("name", flat=True))})'
                for f in found_families if f.family_id not in update_family_ids
            ]
            logger.info(f'Skipping {num_found - len(families)} families with analysis groups in the project: {", ".join(group_families)}')

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
