from django.core.management.base import BaseCommand
from django.db.models.functions import Replace
from django.db.models import Value, prefetch_related_objects

from collections import defaultdict
from csv import DictWriter
import json
import re

from seqr.models import Individual, ProjectCategory

FILE_PATH = '/Users/hsnow/Downloads/gcnv_settings_v3.json'

KNOWN_INDIVIDUAL_TYPES = {
    'RGP_9_1': 'WES', 'RGP_9_2': 'WES', 'RGP_9_3': 'WES', 'RGP_9_4': 'WES', 'RGP_9_5': 'WES', 'RGP_9_6': 'WES',
}

ALLOW_DUPLICATES = {'WAL_MC38900_MC38902', 'WAL_MC38900_MC38901', 'WAL_MC38900_MC38903'}

def _parse_sample_id(sample_id):
    match = re.search('(\d+)_(Exome_)?(?P<sample_id>.+)_v\d_(Exome_GCP|WGS_GCP|tempID)', sample_id)
    if not match:
        raise ValueError(f'Invalid sample: {sample_id}')
    return match.group('sample_id')

class Command(BaseCommand):

    def handle(self, *args, **options):
        with open(FILE_PATH) as f:
            data = json.load(f)
        batch_rows = next(
            category['rows'] for category in data['rowsInCategories'] if category['categoryName'] == 'gCNV Batches')

        gcnv_samples = defaultdict(list)
        for batch in batch_rows:
            assert len(batch['data']) == 1
            batch_data = batch['data'][0]
            assert batch_data['type'] == 'gcnv_bed'
            for sample in batch_data['samples']:
                gcnv_samples[_parse_sample_id(sample)].append({'url': batch_data['url'], 'sample': sample})

        individuals_by_sample_id = defaultdict(list)
        individuals = list(Individual.objects.filter(individual_id__in=gcnv_samples.keys()))
        for i in individuals:
            individuals_by_sample_id[i.individual_id].append(i)
        print(f'Found seqr individuals for {len(individuals_by_sample_id)} samples')

        missing_samples = set(gcnv_samples.keys()) - set(individuals_by_sample_id.keys())

        print(f'Attempting to fuzzy match {len(missing_samples)} missing samples')
        fuzzy_sample_map = {s.replace('-', '_'): s for s in missing_samples}
        fuzzy_match_individuals = Individual.objects.annotate(
            fuzzy_id=Replace('individual_id', Value('-'), Value('_'))).filter(
            fuzzy_id__in=fuzzy_sample_map.keys())
        individuals += list(fuzzy_match_individuals)
        matched_samples = set()
        for i in fuzzy_match_individuals:
            sample_id = fuzzy_sample_map[i.individual_id.replace('-', '_')]
            individuals_by_sample_id[sample_id].append(i)
            matched_samples.add(sample_id)

        missing_samples -= matched_samples
        print(f'Resolved {len(matched_samples)} missing samples')

        print(f'Mapping {len(individuals_by_sample_id)} samples (skipping {len(missing_samples)})')

        prefetch_related_objects(individuals, 'sample_set')
        prefetch_related_objects(individuals, 'family__project')
        cmg_projects = ProjectCategory.objects.get(name='CMG').projects.all()

        individual_samples = {}
        duplicate_individuals = set()
        mismatch_type_samples = set()
        for sample_id, individuals in individuals_by_sample_id.items():
            samples = gcnv_samples[sample_id]
            assert samples
            # Match samples to appropriate sample types
            has_duplicates = False
            allowed_duplicate_individuals = None
            individual_type_map = {_get_individual_sample_type(indiv): indiv for indiv in individuals}
            if len(individual_type_map) < len(individuals):
                has_duplicates = True
                if len(individuals) > 1 and all(indiv.family.project.name == 'CMG_Hildebrandt_Exomes' for indiv in individuals):
                    # CMG_Hildebrandt_Exomes has some duplicated families, we should use the active ones
                    individuals = [indiv for indiv in individuals if indiv.family.family_id.startswith('HIL_')]
                else:
                    # Prefer internal CMG projects
                    individuals = [indiv for indiv in individuals if indiv.family.project in cmg_projects and indiv.family.project.name != 'Estonian External Exomes']
                individual_type_map = {_get_individual_sample_type(indiv): indiv for indiv in individuals}
                if len(individual_type_map) < len(individuals):
                    if sample_id in ALLOW_DUPLICATES and len(samples) == 1 and list(individual_type_map.keys()) == [_get_gcnv_sample_type(samples[0])]:
                        allowed_duplicate_individuals = individuals
                    else:
                        raise ValueError(f'Duplicate CMG seqr individuals exist for sample {sample_id}')

            sample_type_map = {_get_gcnv_sample_type(sample): sample for sample in samples}
            if len(sample_type_map) < len(samples):
                # Remove samples with identical IDs, and those in the straggler cluster if real clusters exist
                samples = list({sample['sample']: sample for sample in samples if 'cluster_straggler' not in sample['url']}.values())
                assert samples
                sample_type_map = {_get_gcnv_sample_type(sample): sample for sample in samples}
                if len(sample_type_map) < len(samples):
                    if has_duplicates:
                        duplicate_individuals.add(sample_id)
                        continue

                    sample_type_map = {}
                    for sample in samples:
                        sample_type = _get_gcnv_sample_type(sample)
                        existing = sample_type_map.get(sample_type)
                        if existing:
                            existing_version_match = re.search('_(?P<version>\d)$', existing['sample'])
                            existing_version = int(existing_version_match.group('version')) if existing_version_match else None
                            new_version_match = re.search('_(?P<version>\d)$', sample['sample'])
                            new_version = int(new_version_match.group('version')) if new_version_match else None
                            if existing_version and new_version:
                                if new_version == existing_version:
                                    raise ValueError('Duplicate samples with the same version: {} and {}'.format(
                                        existing['sample'], sample['sample']))
                                if new_version > existing_version:
                                    sample_type_map[sample_type] = sample
                            elif new_version:
                                sample_type_map[sample_type] = sample
                            elif not existing_version:
                                raise ValueError('Duplicate samples with no specified version: {} and {}'.format(
                                    existing['sample'], sample['sample']))
                        else:
                            sample_type_map[sample_type] = sample

            for sample_type, sample in sample_type_map.items():
                if allowed_duplicate_individuals:
                    for individual in allowed_duplicate_individuals:
                        individual_samples[individual] = sample
                    continue

                individual = individual_type_map.get(sample_type)
                if not individual:
                    if len(samples) == 1 and len(individuals) == 1:
                        indiv_type = list(individual_type_map.keys())[0]
                        if indiv_type is None or sample_type is None:
                            individual = individual_type_map[indiv_type]

                if not individual:
                    if len(samples) != 1:
                        raise ValueError(f'Unable to map sample type {sample_type} for {sample_id}: individual types {individual_type_map.keys()}')

                    full_sample_id = re.search('(?P<sample_id>.+)_v\d_(Exome_GCP|WGS_GCP|tempID)', samples[0]['sample']).group('sample_id')
                    fuzzy_sample_ids = [s.replace('-', '_') for s in [sample_id, full_sample_id]]
                    fuzzy_individuals = Individual.objects.annotate(
                        fuzzy_id=Replace('individual_id', Value('-'), Value('_'))
                    ).filter(fuzzy_id__in=fuzzy_sample_ids).exclude(id__in=[ind.id for ind in individuals])
                    fuzzy_match_indivs_by_type = defaultdict(list)
                    for indiv in fuzzy_individuals:
                        if indiv.family.project.name != 'INMR Family T':
                            fuzzy_match_indivs_by_type[_get_individual_sample_type(indiv)].append(indiv)
                    fuzzy_match_type_indivs = fuzzy_match_indivs_by_type[sample_type] or fuzzy_match_indivs_by_type[None]
                    if len(fuzzy_match_type_indivs) == 1:
                        individual = fuzzy_match_type_indivs[0]
                    else:
                        mismatch_type_samples.add(sample_id)
                        continue

                individual_samples[individual] = sample

        print(f'Successfully mapped {len(individual_samples)} samples')
        duplicates = ', '.join(sorted(duplicate_individuals))
        print(f'Skipping {len(duplicate_individuals)} samples with duplicates: {duplicates}')
        mismatches = ', '.join(sorted(mismatch_type_samples))
        print(f'Skipping {len(mismatch_type_samples)} samples with mismatched sample types: {mismatches}')

        project_samples = defaultdict(list)
        for indiv, sample in individual_samples.items():
            project_samples[indiv.family.project.guid].append(dict(individual_id=indiv.individual_id, **sample))

        print(f'Exporting {len(project_samples)} projects')
        for project, samples in project_samples.items():
            with open(f'gcnv_samples/{project}.csv', 'w') as f:
                writer = DictWriter(f, fieldnames=['individual_id', 'url', 'sample'])
                writer.writerows(samples)
        print('Done')


def _get_gcnv_sample_type(sample):
    if 'WGS' in sample['sample']:
        return 'WGS'
    elif 'Exome' in sample['sample']:
        return 'WES'
    return None


def _get_individual_sample_type(indiv):
    types = {s.sample_type for s in indiv.sample_set.all()}
    if len(types) == 0:
        return None
    elif len(types) == 1:
        return list(types)[0]
    elif indiv.individual_id in KNOWN_INDIVIDUAL_TYPES:
        return KNOWN_INDIVIDUAL_TYPES[indiv.individual_id]
    raise ValueError(f'Inconsistent individual sample types for {sample_id}: {types}')