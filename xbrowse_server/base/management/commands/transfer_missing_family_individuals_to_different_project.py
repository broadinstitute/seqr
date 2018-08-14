from django.core.management.base import BaseCommand
from seqr.views.apis.pedigree_image_api import update_pedigree_images

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual
from xbrowse_server.base.model_utils import create_xbrowse_model, update_xbrowse_model

from collections import defaultdict
"""
This was created to fix a one time issue with transfering families in which all the parents were dropped
(https://github.com/macarthur-lab/seqr-private/issues/335)

If transfers are done using the transfer_families_to_different_project command this problem shouldn't happen, so 
this probably shouldn't be used again.
"""

INDIVIDUAL_FIELDS = [
    'indiv_id',
    'maternal_id',
    'paternal_id',
    'gender',
    'affected',
    'nickname',
    'other_notes',
    'case_review_status',
    'case_review_status_last_modified_date',
    'case_review_status_last_modified_by',
    'case_review_discussion',
    'phenotips_data',
]

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)

    def handle(self, *args, **options):
        to_project = BaseProject.objects.get(project_id=options['to_project'])
        from_project = BaseProject.objects.get(project_id=options['from_project'])

        to_families = {
            f.family_id: {'family': f, 'individual_ids': [i.indiv_id for i in f.individual_set.only('indiv_id').all()]}
            for f in BaseFamily.objects.filter(project=to_project).only('family_id').prefetch_related('individual_set')
        }
        from_families = {
            f.family_id: {'family': f, 'individuals': f.individual_set.all()}
            for f in BaseFamily.objects.filter(
                project=from_project, family_id__in=to_families.keys()
            ).only('family_id').prefetch_related('individual_set')
        }

        missing_to_family_individuals = {
            family_id: [i for i in from_families[family_id]['individuals'] if i.indiv_id not in family_dict['individual_ids']]
            for family_id, family_dict in to_families.items()
        }

        missing_individual_counts = defaultdict(int)
        missing_individuals = []
        updated_families = set()
        for family_id, individuals in missing_to_family_individuals.items():
            missing_individual_counts[len(individuals)] += 1
            missing_individuals += individuals
            updated_families.add(to_families[family_id]['family'])

        print('Transferring individuals from {} to {}:'.format(from_project.project_name, to_project.project_name))

        for individual in missing_individuals:
            create_xbrowse_model(
                BaseIndividual,
                project=to_project,
                family=to_families[individual.family.family_id]['family'],
                **{field: getattr(individual, field) for field in INDIVIDUAL_FIELDS}
            )

        for family in updated_families:
            update_xbrowse_model(family, pedigree_image=from_families[family.family_id]['family'].pedigree_image)

        for num_individuals, num_families in missing_individual_counts.items():
            print('Added {} individuals to {} families'.format(num_individuals, num_families))

        print("Done.")
