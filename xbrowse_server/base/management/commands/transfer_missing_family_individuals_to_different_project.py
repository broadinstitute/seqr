from django.core.management.base import BaseCommand

from seqr.models import Sample as SeqrSample
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual, \
    VCFFile
from xbrowse_server.base.model_utils import get_or_create_xbrowse_model, update_xbrowse_model

from collections import defaultdict
"""
This was created to fix a one time issue with transfering families in which all the parents were dropped
(https://github.com/macarthur-lab/seqr-private/issues/335)

If transfers are done using the transfer_families_to_different_project command this problem shouldn't happen, so 
this probably shouldn't be used again.
"""

INDIVIDUAL_FIELDS = [
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

SHARED_SAMPLE_FIELDS = [
    'dataset_type',
    'sample_type',
    'elasticsearch_index',
    'loaded_date'
]

VCF_FILE_FIELDS = ['file_path'] + SHARED_SAMPLE_FIELDS

SAMPLE_FIELDS = ['sample_id', 'dataset_name', 'dataset_file_path', 'sample_status'] + SHARED_SAMPLE_FIELDS


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-project', required=True)
        parser.add_argument('--to-project', required=True)

    def handle(self, *args, **options):
        to_project = BaseProject.objects.get(project_id=options['to_project'])
        from_project = BaseProject.objects.get(project_id=options['from_project'])

        to_families = BaseFamily.objects.filter(project=to_project).only('family_id').prefetch_related('individual_set')

        from_families_map = {
            f.family_id: {'family': f, 'individuals': f.individual_set.all()}
            for f in BaseFamily.objects.filter(
                project=from_project, family_id__in=[f.family_id for f in to_families]
            ).only('family_id').prefetch_related('individual_set')
        }

        print('Transferring individuals from {} to {}:'.format(from_project.project_name, to_project.project_name))

        missing_family_individual_counts = defaultdict(int)
        missing_individual_sample_counts = defaultdict(int)
        created_vcf_count = 0
        for family in to_families:
            for from_individual in from_families_map[family.family_id]['individuals']:
                to_individual, individual_created = get_or_create_xbrowse_model(
                    BaseIndividual,
                    project=to_project,
                    family=family,
                    indiv_id=from_individual.indiv_id,
                )
                if individual_created:
                    update_xbrowse_model(
                        to_individual,
                        **{field: getattr(from_individual, field) for field in INDIVIDUAL_FIELDS}
                    )
                missing_family_individual_counts[family] += (1 if individual_created else 0)

                for from_vcf_file in from_individual.vcf_files.all():
                    to_vcf_file, vcf_created = VCFFile.objects.get_or_create(
                        project=to_project,
                        **{field: getattr(from_vcf_file, field) for field in VCF_FILE_FIELDS}
                    )
                    if vcf_created:
                        created_vcf_count += 1
                    to_individual.vcf_files.add(to_vcf_file)

                for from_sample in from_individual.seqr_individual.sample_set.all():
                    to_sample, sample_created = SeqrSample.objects.get_or_create(
                        individual=to_individual.seqr_individual,
                        **{field: getattr(from_sample, field) for field in SAMPLE_FIELDS}
                    )
                    missing_individual_sample_counts[to_individual] += (1 if sample_created else 0)

        missing_individual_counts = defaultdict(int)
        updated_families = set()
        for family, individual_count in missing_family_individual_counts.items():
            missing_individual_counts[individual_count] += 1
            if individual_count > 0:
                updated_families.add(family)

        missing_sample_counts = defaultdict(int)
        for individual, sample_count in missing_individual_sample_counts.items():
            missing_sample_counts[sample_count] += 1
            if sample_count > 0:
                updated_families.add(individual.family)

        for family in updated_families:
            update_xbrowse_model(family, pedigree_image=from_families_map[family.family_id]['family'].pedigree_image)

        print("Done.")
        print("----------------------------------------------")
        for num_individuals, num_families in missing_individual_counts.items():
            print('Added {} individuals to {} families'.format(num_individuals, num_families))
        print("----------------------------------------------")
        print('Added {} VCF files'.format(created_vcf_count))
        print("----------------------------------------------")
        for num_samples, num_individuals in missing_sample_counts.items():
            print('Added {} samples to {} individuals'.format(num_samples, num_individuals))
