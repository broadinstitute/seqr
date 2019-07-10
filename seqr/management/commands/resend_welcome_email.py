from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from seqr.views.apis.users_api import send_welcome_email

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-e', '--email-address', required=True, help="Email address")
        parser.add_argument('-r', '--referrer', required=True, help="Who the email should be from")

    def handle(self, *args, **options):
        user = User.objects.get(email__iexact=options['email_address'])
        referrer = User.objects.get(email__iexact=options['referrer'])
        send_welcome_email(user, referrer)
