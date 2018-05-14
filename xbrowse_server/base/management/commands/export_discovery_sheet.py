from django.test.client import RequestFactory
from django.core.management.base import BaseCommand
from seqr.views.pages.staff.discovery_sheet import discovery_sheet
from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        GET_request = RequestFactory().get('/staff/discovery_sheet/?download')
        GET_request.user = User()
        GET_request.user.is_staff = True
        response = discovery_sheet(GET_request)
        with open("discovery_sheet.xls", "w") as f:
            f.write(response.content)

        
