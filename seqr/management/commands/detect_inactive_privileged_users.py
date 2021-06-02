from anymail.exceptions import AnymailError
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

WARNING_TEMPLATE = """
Hi there {} - 

You have not logged in to seqr in {} days. Unless you log in within the next {} days, your account will be deactivated.
"""

DEACTIVATE_TEMPLATE = """
Hi there {} - 

You have not logged in to seqr in {} days, and therefore your account has been deactivated.
Please feel free to reach out to the seqr team if you would like your account reinstated.
"""

class Command(BaseCommand):


    def handle(self, *args, **options):
        logger.info('Checking for inactive users')

        now = datetime.now()
        required_login = now - timedelta(days=90)
        warn_login = required_login + timedelta(days=30)

        users = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).filter(is_active=True)
        deactivate_users = users.filter(last_login__lt=required_login)
        warn_users = users.filter(last_login__lt=warn_login, last_login__gt=required_login)

        for user in warn_users:
            logger.info('Warning {} of impending account inactivation'.format(user.email))
            days_login = (now - user.last_login.replace(tzinfo=None)).days
            email_content = WARNING_TEMPLATE.format(user.get_full_name(), days_login, 90 - days_login)
            try:
                user.email_user('Warning: seqr account deactivation', email_content)
            except AnymailError as e:
                logger.error('Unable to send email: {}'.format(e))

        for user in deactivate_users:
            logger.info('Inactivating account for {}'.format(user.email))
            user.is_active = False
            user.save()

            days_login = (now - user.last_login.replace(tzinfo=None)).days
            email_content = DEACTIVATE_TEMPLATE.format(user.get_full_name(), days_login)
            try:
                user.email_user('Warning: seqr account deactivated', email_content)
            except AnymailError as e:
                logger.error('Unable to send email: {}'.format(e))

        logger.info('Inactive user check complete')

