import csv
import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.base.models import Project
from xbrowse_server.mall import get_mall, get_reference
from xbrowse.variant_search.family import get_variants

def get_gene_symbol(variant):
    gene_id = variant.annotation['vep_annotation'][
        variant.annotation['worst_vep_annotation_index']]['gene']
    return get_reference().get_gene_symbol(gene_id)



class Command(BaseCommand):

    def handle(self, *args, **options):
        if not args:
            sys.exit("ERROR: please specify project id on the command line")
        if len(args) > 1:
            sys.exit("ERROR: too many args: %s. Only one project id should be provided." % " ".join(args) )

        project_id = args[0]

        individuals_file = args[1]
        with open(individuals_file) as f:
            for line in individuals_file:
                individual_id = line.split("\t")

        # filter
        variant_filter = get_default_variant_filter('moderate_impact')
        variant_filter.ref_freqs.append(('g1k_all', 0.01))
        variant_filter.ref_freqs.append(('exac', 0.01))
        variant_filter.ref_freqs.append(('exac-popmax', 0.01))
        variant_filter.ref_freqs.append(('merck-wgs-3793', 0.05))
        quality_filter = {
            'filter': 'pass',
            'min_gq': 30,
            'min_ab': 15,
        }

        # create individuals_variants.tsv
        individual_variants_f = gzip.open('individuals_in_%s.tsv.gz' % project_id, 'w')
        writer = csv.writer(individual_variants_f, dialect='excel', delimiter='\t')

        header_fields = [
            'project_id',
            'family_id',
            'individual_id',
            'gene',
            'chrom',
            'pos',
            'ref',
            'alt',
            'rsid',
            'annotation',
            'exac_af',
            '1kg_af',
            'exac_popmax_af',
            'merck_wgs_3793_af',
            ]
        writer.writerow(header_fields)
        # collect the resources that we'll need here
        annotator = get_mall(project_id).get_annotator()
        custom_population_store = get_mall(project_id).get_custom_population_store()

        project = Project.objects.get(project_id=project_id)
        families = project.get_families()
        for i, family in enumerate(families):
            for individual in family.get_individuals():
                for variant in get_variants(get_mall(project.project_id).variant_store,
                                            family,
                                            variant_filter = variant_filter,
                                            quality_filter = quality_filter,
                                            indivs_to_consider = [individual.indiv_id]
                                            ):
                    custom_populations = custom_population_store.get_frequencies(variant.xpos, variant.ref, variant.alt)
                    writer.writerow([
                        project_id,
                        family.family_id,
                        individual.indiv_id,
                        get_gene_symbol(variant),
                        variant.chr,
                        str(variant.pos),
                        variant.ref,
                        variant.alt,
                        variant.vcf_id,
                        variant.annotation['vep_group'],
                        str(variant.annotation['freqs']['exac']),
                        str(variant.annotation['freqs']['g1k_all']),
                        str(custom_populations.get('exac-popmax', 0.0)),
                        str(custom_populations.get('merck-wgs-3793', 0.0)),
                    ])

        individual_variants_f.close()

