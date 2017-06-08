from optparse import make_option
from xbrowse_server import xbrowse_controls
from xbrowse_server.user_controls import add_new_collaborator
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project

import signal, traceback
def quit_handler(signum,frame):
    traceback.print_stack()
signal.signal(signal.SIGQUIT,quit_handler)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-e', '--email-address', required=True, help="Email address")
        parser.add_argument('-r', '--referrer', required=True, help="Who the email should be from")

    def handle(self, *args, **options):
        print("Email addr.: %s" %  options['email_address'])
        print("Referrer: %s" %  options['referrer'])
        class FakeUserObj: pass
        u = FakeUserObj()
        u.profile = options['referrer']
        add_new_collaborator(options['email_address'], referrer=u)
