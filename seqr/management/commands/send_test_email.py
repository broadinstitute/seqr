from django.core.management.base import BaseCommand
from django.core.mail.message import EmailMessage


class Command(BaseCommand):
    help = 'Create a new user.'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--email-address', help="Email address", required=True)

    def handle(self, *args, **options):
        email = options['email_address']

        email_message = EmailMessage(
            subject="Test seqr email",
            body="This is a test email",
            to=[email],
        )
        email_message.send()
        print('Email sent')

