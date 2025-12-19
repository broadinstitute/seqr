from django.core.management.base import BaseCommand
import logging
from tqdm import tqdm

from matchmaker.models import MatchmakerSubmission

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('email', help='MME contact email to replace')
        parser.add_argument('--replace-email', '-re', help='optional email to replace with')
        parser.add_argument('--replace-name', '-rn', help='optional name to replace with')

    def handle(self, *args, **options):
        email = options['email']
        replace_email = options['replace_email']
        submissions = MatchmakerSubmission.objects.all()
        num_updated = 0
        skipped = []
        for submission in tqdm(submissions):
            contacts = [contact for contact in submission.contacts if contact['email'] != email]
            if len(contacts) == len(submission.contacts):
                continue
            if replace_email:
                contacts.append({'name': options['replace_name'] or '', 'email': replace_email})
            if not any(c.get('name') for c in contacts):
                skipped.append(submission.label)
                continue
            submission.contacts = contacts
            submission.save()
            num_updated += 1
        logger.info(f'Updated {num_updated} submissions')
        if skipped:
            logger.info(f'Skipped updating submissions with no remaining valid contacts: {", ".join(skipped)}')
        logger.info('Done')
