from collections import defaultdict
import csv
from django.core.management.base import BaseCommand
import elasticsearch
import elasticsearch_dsl
import gzip
import json

import settings
from seqr.models import Individual
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals
from xbrowse_server.base.models import Project as BaseProject

EXCLUDE_PROJECTS = ['ext', '1000 genomes', 'DISABLED', 'project', 'interview', 'non-cmg', 'amel']


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        projects_q = BaseProject.objects.filter(genome_version='37')
        for exclude_project in EXCLUDE_PROJECTS:
            projects_q = projects_q.exclude(project_name__icontains=exclude_project)
        indices_for_project = defaultdict(list)
        for project in projects_q:
            indices_for_project[project.get_elasticsearch_index()].append(project)
        indices_for_project.pop(None, None)

        es_client = elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME, timeout=10000)
        search = elasticsearch_dsl.Search(using=es_client, index='*,'.join(indices_for_project.keys()) + "*")
        search = search.query("match", mainTranscript_lof='HC')
        search = search.source(['contig', 'pos', 'ref', 'alt', '*num_alt'])

        print('Searching...')
        results = []
        for i, hit in enumerate(search.scan()):
            result = {key: hit[key] for key in hit}
            result['index'] = hit.meta.index
            results.append(result)

        print('Loaded {} variants'.format(len(results)))
        with gzip.open('lof_variants.json.gz', 'w') as f:
            json.dump(results, f)

        seqr_projects = []
        with open('project_indices.csv', 'wb') as csvfile:
            fieldnames = ['projectGuid', 'index']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for index, projects in indices_for_project.items():
                for project in projects:
                    seqr_projects.append(project.seqr_project)
                    writer.writerow({'projectGuid': project.seqr_project.guid, 'index': index})

        individuals = _get_json_for_individuals(Individual.objects.filter(family__project__in=seqr_projects))
        with open('seqr_individuals.csv', 'wb') as csvfile:
            fieldnames = ['projectGuid', 'familyGuid', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for individual in individuals:
                writer.writerow(individual)

        print('output written to files')