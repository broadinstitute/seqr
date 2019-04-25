import logging
import pymongo
import settings

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from seqr.models import Project, Individual

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer MME data to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('project_guid', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        project_ids_to_process = options['project_guid']

        if project_ids_to_process:
            projects = Project.objects.filter(guid__in=project_ids_to_process)
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.all()
            logging.info("Processing all %s projects" % len(projects))

        errors = []
        stats = {}
        for project in projects:
            num_transferred, project_errors = transfer_mme_submission_data(project)
            errors += project_errors
            if num_transferred:
                stats[project.name] = num_transferred

        logger.info("Done")
        logger.info("Stats: ")
        for project in sorted(stats.keys()):
            logger.info('{}: {} submissions'.format(project, stats[project]))
        if errors:
            logger.info("ERRORS: ")
            for error in errors:
                logger.error(error)


def transfer_mme_submission_data(project):
    mongo_mme_submissions = settings._client['mme_primary']['seqr_id_to_mme_id_map']
    submissions = mongo_mme_submissions.find({'project_id': project.deprecated_project_id}).sort(
        'insertion_date', pymongo.DESCENDING
    )

    errors = []
    if submissions and not project.is_mme_enabled:
        errors.append('{} is disabled for MME but has {} submissions'.format(project.name, len(submissions)))

    updated_individuals = set()
    individuals_by_id = {i.individual_id: i for i in Individual.objects.filter(family__project=project)}

    invalid_individuals = set()
    for submission in submissions:
        if submission['seqr_id'] in updated_individuals:
            continue

        individual = individuals_by_id.get(submission['seqr_id'])
        if not individual:
            possible_indivs = [
                i for i in individuals_by_id.keys()
                if i.startswith(submission['seqr_id']) or submission['seqr_id'].startswith(i)
            ]
            if len(possible_indivs) == 1:
                use_indiv_id = raw_input(
                    'No match found for {}. Use {} instead? (y/n) '.format(submission['seqr_id'], possible_indivs[0]))
                if use_indiv_id == 'y':
                    individual = individuals_by_id[possible_indivs[0]]

            if not individual:
                invalid_individuals.add(submission['seqr_id'])
                continue

        if individual.mme_submitted_date:
            continue

        submitted_data = submission['submitted_data']
        if submitted_data:
            individual.mme_submitted_data = submitted_data
            individual.mme_id = submitted_data['patient']['id']
            individual.mme_submitted_date = submission['insertion_date']
            if submission.get('deletion'):
                individual.mme_deleted_by = User.objects.filter(username=submission['deletion']['by']).first()
                individual.mme_deleted_date = submission['deletion']['date']
            individual.save()
            updated_individuals.add(submission['seqr_id'])

    if invalid_individuals:
        errors.append('{}: Could not find individuals {}'.format(project.name, ', '.join(invalid_individuals)))

    return len(updated_individuals), errors
