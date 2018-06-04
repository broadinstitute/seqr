import csv
import gzip
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter, VariantFilter
from xbrowse.variant_search.family import get_variants_with_inheritance_mode, get_variants
from xbrowse_server import mall
from xbrowse_server.base.models import Project, Family
from xbrowse_server.mall import get_mall, get_reference, get_datastore


#AB_threshold = 25
#GQ_threshold = 20
#DP_threshold = 10

#g1k_freq_threshold = 0.01
#g1k_popmax_freq_threshold = 0.01
exac_freq_threshold = 0.01
exac_popmax_threshold = 0.01
gnomad_exomes_threshold = 0.01
gnomad_genomes_threshold = 0.01



def get_gene_symbol(variant):
    gene_id = variant.annotation['vep_annotation'][
        variant.annotation['worst_vep_annotation_index']]['gene']
    return get_reference().get_gene_symbol(gene_id)


def get_variants_for_inheritance_for_project(project):
    """
    Get the variants for this project / inheritance combo
    Return dict of family -> list of variants
    """

    #variant_filter.genes = ['ENSG00000067715']  # SYT1
    #variant_filter = VariantFilter(so_annotations=SO_SEVERITY_ORDER, ref_freqs=[])

    variant_filter = get_default_variant_filter('moderate_impact')
    variant_filter.ref_freqs.append(('exac_v3', exac_freq_threshold))
    variant_filter.ref_freqs.append(('exac_v3_popmax', exac_popmax_threshold))
    variant_filter.ref_freqs.append(('gnomad-exomes', gnomad_exomes_threshold))
    variant_filter.ref_freqs.append(('gnomad-genomes', gnomad_genomes_threshold))
    quality_filter = None

    families = project.get_families()
    for i, family in enumerate(families):
        counter = 0
        for inheritance_mode in ['homozygous_recessive']: # , 'compound_het', 'x_linked_recessive']: #, 'dominant', 'de_novo', 'all_variants']:

            print("Processing %s - family %s  (%d / %d)" % (inheritance_mode, family.family_id, i+1, len(families)))
            try:
                counter += len(list(get_variants_with_inheritance_mode(
                    get_mall(project),
                    family.xfamily(),
                    inheritance_mode,
                    variant_filter=variant_filter,
                    quality_filter=quality_filter,
                )))

            except ValueError as e:
                print("Error: %s. Skipping family %s" % (str(e), str(family)))

        yield family, counter

def handle_project(project):
    filename = 'family_variants.tsv.gz'
    print("Computing for project: " + str(project))

    # create family_variants.tsv
    family_variants_f = gzip.open(filename, 'a+')
    writer = csv.writer(family_variants_f, dialect='excel', delimiter='\t')
    header_fields = [
        'project_id',
        'family_id',
        'count',
        'number of individuals in family']

    #writer.writerow(header_fields)
    family_variants_f.close()

    # get the variants for this inheritance / project combination
    for i, (family, family_results) in enumerate(get_variants_for_inheritance_for_project(project)):
        """
        for variant in family_results:
            g1k_freq = variant.annotation['freqs']['1kg_wgs_phase3']
            g1k_popmax_freq = variant.annotation['freqs']['1kg_wgs_phase3_popmax']
            exac_freq = variant.annotation['freqs']['exac_v3']
            exac_popmax_freq =  variant.annotation['freqs']['exac_v3_popmax']
            gnomad_exomes_freq = custom_populations.get('gnomad-exomes', 0.0)
            gnomad_genomes_freq = custom_populations.get('gnomad-genomes', 0.0)

            try:
                assert g1k_freq <= g1k_freq_threshold, "g1k freq %s > %s" % (g1k_freq, g1k_freq_threshold)
                assert g1k_popmax_freq <= g1k_popmax_freq_threshold, "g1k freq %s > %s" % (g1k_popmax_freq, g1k_popmax_freq_threshold)
                assert exac_freq <= exac_freq_threshold, "Exac freq %s > %s" % (exac_freq, exac_freq_threshold)
                assert exac_popmax_freq <= exac_popmax_threshold, "Exac popmax freq %s > %s" % (exac_popmax_freq, exac_popmax_threshold)
                assert gnomad_genomes_freq <= gnomad_genomes_threshold, "Gnomad genomes threshold %s > %s" % (gnomad_genomes_freq, gnomad_genomes_threshold)
                assert gnomad_exomes_freq <= gnomad_exomes_threshold, "Gnomad exomes threshold %s > %s" % (gnomad_exomes_freq, gnomad_exomes_threshold)
            except AssertionError as e:
                import traceback
                traceback.print_exc()
        """

        # filter value is stored in the genotypes
        n_individuals = len(family.get_individuals())
        if n_individuals == 0:
            print("Family has 0 individuals: %s - skipping..." % str(family))
            continue

        row = [
            project.project_id,
            family.family_id,
            family_results,
            n_individuals,
        ]

        print("Writing out row: " + ','.join(map(str, row)))
        family_variants_f = gzip.open(filename, 'a+')
        writer = csv.writer(family_variants_f, dialect='excel', delimiter='\t')

        writer.writerow(row)
        family_variants_f.close()
    print("Done with " + filename)



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        import os
        os.remove('family_variants.tsv.gz')
        if args:
            projects = Project.objects.filter(project_id__in=args)
        else:
            projects = Project.objects.all()

        for project in projects:
            print(project)
            handle_project(project)
            print("----------")