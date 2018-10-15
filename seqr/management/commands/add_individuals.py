import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from seqr.models import Project
from seqr.utils.file_utils import file_iter

from seqr.views.apis.individual_api import add_or_update_individuals_and_families
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table

logger = logging.getLogger(__name__)


def add_individuals_from_pedigree_file(project, pedigree_file_path, validate_only=False):
    if pedigree_file_path and not os.path.isfile(pedigree_file_path):
        raise CommandError("Can't open pedigree file: %(pedigree_file)s" % locals())

    # parse the pedigree file if specified
    input_stream = file_iter(pedigree_file_path)
    json_records, errors, warnings = parse_pedigree_table(pedigree_file_path, input_stream)

    if errors:
        for message in errors:
            logger.error(message)
        raise CommandError("Unable to parse %(pedigree_file_path)s" % locals())

    if warnings:
        for message in warnings:
            logger.warn(message)

    if not validate_only:
        add_or_update_individuals_and_families(project, json_records)


class Command(BaseCommand):
    help = """Adds or updates individuals in a project"""

    def add_arguments(self, parser):
        parser.add_argument("--validate-only", action="store_true", help="Only validate the pedigree file, and don't add or update anything.")
        parser.add_argument("project_id", help="Project to which these individuals should be added (eg. R0202_tutorial)")
        parser.add_argument("pedigree_file", help="Format: .tsv, .fam, or .xls. These individuals will be added to the project (or updated if they already exist in the project).")

    def handle(self, *args, **options):

        # parse and validate args
        validate_only = options["validate_only"]
        project_guid = options["project_id"]
        pedigree_file_path = options["pedigree_file"]

        # look up project id and validate other args
        try:
            project = Project.objects.get(guid=project_guid)
        except ObjectDoesNotExist:
            raise CommandError("Invalid project id: %(project_guid)s" % locals())

        add_individuals_from_pedigree_file(project, pedigree_file_path, validate_only=validate_only)
