from django.core.management.base import BaseCommand
from pprint import pprint
import logging

from django.test import Client
from django.contrib.auth.models import User
from django.urls.base import reverse

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('project_id')
        parser.add_argument('gene_id')


    def handle(self, *args, **options):
        user = User.objects.filter(is_superuser=True)[0]
        assert user.is_authenticated()

        c = Client()
        c.force_login(user)
        project_id = options.get('project_id')
        gene_id = options.get('gene_id')

        response = c.get(reverse('project_gene_quicklook', args=[project_id, gene_id]) + "?download=knockouts&selected_projects={}".format(project_id))
        with open("knockouts_in_{}_{}.csv".format(project_id, gene_id), 'w') as f:
            f.write(response.content)

        response = c.get(reverse('project_gene_quicklook', args=[project_id, gene_id]) + "?download=rare_variants&selected_projects={}".format(project_id))
        with open("rare_variants_in_{}_{}.csv".format(project_id, gene_id), 'w') as f:
            f.write(response.content)
