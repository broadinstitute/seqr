from django.core.management.base import BaseCommand

from seqr.models import Project, Family, VariantTag, VariantTagType
from seqr.utils.search.utils import backend_specific_call

import logging
logger = logging.getLogger(__name__)


def _validate_no_search_families(families):
    search_families = families.filter(individual__sample__is_active=True).distinct().values_list('family_id', flat=True)
    if search_families:
        logger.info(f'Unable to transfer the following families with loaded search data: {", ".join(search_families)}')
    return families.exclude(individual__sample__is_active=True)


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
        logger.info('Found {} out of {} families. No match for: {}.'.format(len(families), len(set(family_ids)), ', '.join(set(family_ids) - set([f.family_id for f in families]))))

        families = backend_specific_call(lambda f: f, _validate_no_search_families)(families)

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
