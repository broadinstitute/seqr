import asciitree
from asciitree.util import *
from asciitree.drawing import *

import logging
from collections import OrderedDict
from pprint import pprint

from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import Project, Family, Individual, Sample

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Print a tree of projects.'

    def add_arguments(self, parser):
        parser.add_argument('project_id', nargs="*")

    def handle(self, *args, **options):

        if not options["project_id"]:
            projects = Project.objects.all()
        else:
            projects = []
            for project_id in options["project_id"]:
                matched_projects = Project.objects.filter(Q(guid__icontains=project_id) | Q(name__icontains=project_id))
                if not matched_projects:
                    logger.warn("No matching project found for keyword: %s" % project_id)
                projects.extend(matched_projects)

        projects_tree = OrderedDict()
        for project_i, project in enumerate(projects):
            project_label = "P%s project: %s. GRCh%s" % (project_i + 1, project, project.genome_version)
            project_tree = projects_tree[project_label] = OrderedDict()
            for family_i, family in enumerate(Family.objects.filter(project=project)):
                family_label = "F%s family: %s" % (family_i + 1, family, )
                family_tree = project_tree[family_label] = OrderedDict()
                for individual_i, individual in enumerate(Individual.objects.filter(family=family)):
                    individual_label = "I%s individual: %s" % (individual_i + 1, individual, )
                    individual_tree = family_tree[individual_label] = OrderedDict()
                    for sample_i, sample in enumerate(Sample.objects.filter(individual=individual)):
                        sample_label = "S%s sample: %s" % (sample_i+1, "{sample_type}, elasticsearch_index: {elasticsearch_index} {dataset_file_path}".format(**sample.json()), )
                        individual_tree[sample_label] = OrderedDict()

        #pprint(projects_tree)
        print(apply(
            asciitree.LeftAligned(draw=asciitree.BoxStyle(gfx=asciitree.drawing.BOX_HEAVY, horiz_len=1)),
            [{'Projects:': projects_tree}]
        ))
