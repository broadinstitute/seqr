from django.core.management.base import BaseCommand
from tqdm import tqdm

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Individual


class Command(BaseCommand):

    def handle(self, *args, **options):
        updates = []
        individuals = Individual.objects.filter(
            mme_deleted_date__isnull=True, mme_submitted_data__patient__genomicFeatures__isnull=False
        )

        print('checking {} individuals for invalid genome build'.format(len(individuals)))
        for individual in tqdm(individuals, unit='individuals '):
            updated = False
            for feature in individual.mme_submitted_data['patient']['genomicFeatures']:
                if 'assembly' in feature.get('variant', {}) and \
                        feature['variant']['assembly'] in GENOME_VERSION_LOOKUP:
                    feature['variant']['assembly'] = GENOME_VERSION_LOOKUP[feature['variant']['assembly']]
                    updated = True
            if updated:
                updates.append(individual.individual_id)
                individual.save()

        print('Updated the following {} individuals genome build: {}'.format(len(updates), ', '.join(updates)))