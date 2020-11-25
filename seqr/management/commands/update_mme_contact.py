from django.core.management.base import BaseCommand
import logging
from tqdm import tqdm

from matchmaker.models import MatchmakerSubmission

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('email', help='MME contact email to replace')
        parser.add_argument('--replace-email', '-r', help='optional email to replace with')

    def handle(self, *args, **options):
        email = options['email']
        replace_email = options['replace_email'] or ''
        submissions = MatchmakerSubmission.objects.filter(contact_href__contains=email)
        logger.info('Updating {} submissions'.format(len(submissions)))
        for submission in tqdm(submissions):
            contact = submission.contact_href
            if not replace_email:
                contact = contact.replace('{},'.format(email), replace_email)
            submission.contact_href = contact.replace(email, replace_email).rstrip().rstrip(',')
            submission.save()
        logger.info('Done')
