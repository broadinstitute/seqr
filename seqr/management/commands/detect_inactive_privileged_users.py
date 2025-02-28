from anymail.exceptions import AnymailError
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

WARNING_TEMPLATE = """
Hi there {user} - 

You have not logged in to seqr in {days_login} days. Unless you log in within the next {deactivate_days_login} days, your account will be deactivated.
"""

DEACTIVATE_TEMPLATE = """
Hi there {user} - 

You have not logged in to seqr in {days_login} days, and therefore your account has been deactivated.
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
            self._safe_email_user(user, WARNING_TEMPLATE, 'deactivation')

        for user in deactivate_users:
            logger.info('Inactivating account for {}'.format(user.email))
            user.is_active = False
            user.save()
            self._safe_email_user(user, DEACTIVATE_TEMPLATE, 'deactivated')

        logger.info('Inactive user check complete')

    @staticmethod
    def _safe_email_user(user, email_template, event):
        days_login = (datetime.now() - user.last_login.replace(tzinfo=None)).days
        email_content = email_template.format(
            user=user.get_full_name(), days_login=days_login, deactivate_days_login=90 - days_login,
        )
        try:
            user.email_user(f'Warning: seqr account {event}', email_content)
        except AnymailError as e:
            logger.error('Unable to send email: {}'.format(e))

