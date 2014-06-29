from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from xbrowse import vcf_stuff


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--population'),
        make_option('--vcf-file'),
        make_option('--samples-file'),
    )

    def handle(self, *args, **options):

        datastore = settings.POPULATION_DATASTORE
        population = options.get('population')
        if not population: raise
        vcf_file = options.get('vcf_file')
        samples_file = options.get('samples_file')

        if samples_file:
            samples = [a for a in [line.strip() for line in open(samples_file)] if a]
        else:
            samples = vcf_stuff.get_ids_from_vcf_path(vcf_file)

        for indiv_id in samples:
            datastore.add_individual(population, indiv_id)

        datastore.add_family(
            project_id=population,
            family_id="control_cohort",
            individuals=samples,
        )

        datastore.load_family(
            project_id=population,
            family_id="control_cohort",
            vcf_file_path=vcf_file,
            reference_populations=settings.XBROWSE_REFERENCE_POPULATIONS
        )

