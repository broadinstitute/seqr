import logging
import pymongo
import settings

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from seqr.models import Project, Individual, MatchmakerResult

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer MME data to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('project_guid', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')
        parser.add_argument('--use-near-id-matches', action="store_true", help="If no matching individual ID is found, use closely matching IDs")

    def handle(self, *args, **options):
        project_ids_to_process = options['project_guid']

        if project_ids_to_process:
            projects = Project.objects.filter(guid__in=project_ids_to_process)
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.all()
            logging.info("Processing all %s projects" % len(projects))

        errors = []
        submission_stats = {}
        results_stats = {}
        for project in projects:
            num_transferred, project_errors = transfer_mme_submission_data(project, use_near_id_matches=options['use_near_id_matches'])
            errors += project_errors
            if num_transferred:
                submission_stats[project.name] = num_transferred

            num_transferred, project_errors = transfer_mme_results_data(project, use_near_id_matches=options['use_near_id_matches'])
            errors += project_errors
            if num_transferred:
                results_stats[project.name] = num_transferred

        logger.info("Done")
        logger.info("Stats: ")
        projects = set(results_stats.keys())
        projects.update(submission_stats.keys())
        for project in sorted(projects):
            logger.info('{}: {} submissions, {} results'.format(
                project, submission_stats.get(project, 0), results_stats.get(project, 0)))
        if errors:
            logger.info("ERRORS: ")
            for error in errors:
                logger.error(error)


def transfer_mme_submission_data(project, use_near_id_matches=False):
    mongo_mme_submissions = settings._client['mme_primary']['seqr_id_to_mme_id_map']
    submissions = mongo_mme_submissions.find({'project_id': project.deprecated_project_id}).sort(
        'insertion_date', pymongo.DESCENDING
    )

    errors = []
    if submissions and submissions.count() > 0 and not project.is_mme_enabled:
        errors.append('{} is disabled for MME but has {} submissions'.format(project.name, submissions.count()))

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
                use_indiv_id = use_near_id_matches or raw_input(
                    'No matching individual found for MME ID {}. Use {} instead? (y/n) '.format(submission['seqr_id'], possible_indivs[0]))
                if use_near_id_matches or use_indiv_id == 'y':
                    individual = individuals_by_id[possible_indivs[0]]

            if not individual:
                input_id = None
                while not individual and input_id != 'no':
                    input_id = raw_input(
                    'No matching individual found for MME ID {}. Enter an id to use instead, or enter "no" to continue '.format(submission['seqr_id']))
                    individual = individuals_by_id.get(input_id)
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


def transfer_mme_results_data(project, use_near_id_matches=False):
    mongo_mme_results = settings._client['mme_primary']['match_result_analysis_state']
    project_results = mongo_mme_results.find({'seqr_project_id': project.deprecated_project_id})
    individuals_by_id = {i.individual_id: i for i in Individual.objects.filter(family__project=project)}
    users_by_username = {u.username: u for u in User.objects.all()}

    errors = []
    if project_results and project_results.count() > 0 and not project.is_mme_enabled:
        errors.append('{} is disabled for MME but has {} match results'.format(project.name,  project_results.count()))

    num_result_updated = 0
    invalid_individuals = set()
    invalid_usernames = set()
    individual_id_map = {}
    for result in project_results:
        if 'id_of_indiv_searched_with' not in result:
            continue

        indiv_id = result['id_of_indiv_searched_with']
        individual = individuals_by_id.get(indiv_id)
        if not individual and indiv_id in individual_id_map:
            individual = individuals_by_id.get(individual_id_map[indiv_id])
        if not individual:
            possible_indivs = [i for i in individuals_by_id.keys() if i.startswith(indiv_id) or indiv_id.startswith(i)]
            if len(possible_indivs) == 1:
                use_indiv_id = use_near_id_matches or raw_input(
                    'No matching individual found for MME ID {}. Use {} instead? (y/n) '.format(indiv_id, possible_indivs[0]))
                if use_near_id_matches or use_indiv_id == 'y':
                    individual = individuals_by_id[possible_indivs[0]]
                    individual_id_map[indiv_id] = possible_indivs[0]
        if not individual:
            invalid_individuals.add(indiv_id)
            continue

        user = users_by_username.get(result['username_of_last_event_initiator'])
        if not user:
            invalid_usernames.add(result['username_of_last_event_initiator'])

        result_model, created = MatchmakerResult.objects.get_or_create(
            individual=individual,
            result_data=result['content_of_result'],
            last_modified_by=user,
            we_contacted=result['we_contacted_host'],
            host_contacted=result['host_contacted_us'],
            deemed_irrelevant=result['deemed_irrelevant'],
            flag_for_analysis=result['flag_for_analysis'],
            comments=result['comments'],
        )

        if created:
            result_model.created_date = result['seen_on']
            result_model.save()
            num_result_updated += 1

    if invalid_individuals:
        errors.append('{}: Could not find individuals {}'.format(project.name, ', '.join(invalid_individuals)))

    if invalid_usernames:
        errors.append('{}: Could not find users {}'.format(project.name, ', '.join(invalid_usernames)))

    return num_result_updated, errors
