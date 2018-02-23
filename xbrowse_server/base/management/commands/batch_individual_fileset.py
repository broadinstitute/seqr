import csv
import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.base.models import Project
from xbrowse_server.mall import get_reference, get_datastore, get_annotator, get_custom_population_store
from xbrowse.variant_search.family import get_variants

def get_gene_symbol(variant):
    gene_id = variant.annotation['vep_annotation'][
        variant.annotation['worst_vep_annotation_index']]['gene']
    return get_reference().get_gene_symbol(gene_id)


AB_threshold = 15
GQ_threshold = 20
DP_threshold = 10
g1k_freq_threshold = 0.01
g1k_popmax_freq_threshold = 0.01
exac_freq_threshold = 0.01
exac_popmax_threshold = 0.01
merck_wgs_3793_threshold = 0.05

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if len(args) != 2:
            sys.exit("ERROR: please specify the project_id and file of individual ids as command line args.")

        project_id = args[0]
        individuals_file = args[1]

        # init objects
        project = Project.objects.get(project_id=project_id)
        all_individual_ids_in_project = set([i.indiv_id for i in project.get_individuals()])

        individuals_of_interest = []
        invalid_individual_ids = []
        with open(individuals_file) as f:
            for line in f:
                line = line.strip('\n')
                if not line or line.startswith("#"):
                    continue
                individual_id = line.split("\t")[0]
                if individual_id in all_individual_ids_in_project:
                    individuals_of_interest.append(individual_id)
                else:
                    invalid_individual_ids.append(individual_id)

        print("Processing %s: %d individuals " % (project_id, len(individuals_of_interest)))
        if invalid_individual_ids:
            num_invalid = len(invalid_individual_ids)
            total_ids = len(all_individual_ids_in_project)
            sys.exit(("ERROR: %(individuals_file)s: %(num_invalid)s out of %(total_ids)s ids are invalid. \nThe invalid ids are: "
                      "%(invalid_individual_ids)s.\nValid ids are: %(individuals_of_interest)s") % locals())

        # filter
        variant_filter = get_default_variant_filter('moderate_impact')
        variant_filter.ref_freqs.append(('1kg_wgs_phase3', g1k_freq_threshold))
        variant_filter.ref_freqs.append(('1kg_wgs_phase3_popmax', g1k_popmax_freq_threshold))
        variant_filter.ref_freqs.append(('exac_v3', exac_freq_threshold))
        variant_filter.ref_freqs.append(('exac_v3_popmax', exac_popmax_threshold))
        variant_filter.ref_freqs.append(('merck-wgs-3793', merck_wgs_3793_threshold))
        quality_filter = {
            'vcf_filter': 'pass',
            'min_gq': GQ_threshold,
            'min_ab': AB_threshold,
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
            '1kg_af',
            '1kg_popmax_af',
            'exac_af',
            'exac_popmax_af',
            'merck_wgs_3793_af',
            'genotype_str',
            'genotype_num_alt',
            'genotype_allele_balance',
            'genotype_AD',
            'genotype_DP',
            'genotype_GQ',
            'genotype_PL',
            'genotype_filter', 
            ]

        writer.writerow(header_fields)
        # collect the resources that we'll need here
        annotator = get_annotator()
        custom_population_store = get_custom_population_store()

        individual_counter = 0
        for i, family in enumerate(project.get_families()):
            for individual in family.get_individuals():
                if individual.indiv_id not in individuals_of_interest:
                    continue
                individual_counter += 1
                print("%s: %s, individual %s" % (individual_counter, family.family_id, individual.indiv_id))
                for variant in get_variants(get_datastore(project),
                                            family.xfamily(),
                                            variant_filter = variant_filter,
                                            quality_filter = quality_filter,
                                            indivs_to_consider = [individual.indiv_id]
                                            ):
                    genotype = variant.get_genotype(individual.indiv_id)
                    if len(genotype.alleles) == 0 or genotype.extras["dp"] < DP_threshold or genotype.num_alt == 0:
                        continue

                    custom_populations = custom_population_store.get_frequencies(variant.xpos, variant.ref, variant.alt)

                    genotype_str = "/".join(genotype.alleles) if genotype.alleles else "./."

                    g1k_freq = variant.annotation['freqs']['1kg_wgs_phase3']
                    g1k_popmax_freq = variant.annotation['freqs']['1kg_wgs_phase3_popmax']
                    exac_freq = variant.annotation['freqs']['exac_v3']
                    exac_popmax_freq = variant.annotation['freqs']['exac_v3_popmax']
                    merck_wgs_3793_freq = custom_populations.get('merck-wgs-3793', 0.0)

                    assert g1k_freq <= g1k_freq_threshold, "g1k freq %s > %s" % (g1k_freq, g1k_freq_threshold)
                    assert g1k_popmax_freq <= g1k_popmax_freq_threshold, "g1k popmax freq %s > %s" % (g1k_popmax_freq, g1k_popmax_freq_threshold)
                    assert exac_freq <= exac_freq_threshold, "Exac freq %s > %s" % (exac_freq, exac_freq_threshold)
                    assert exac_popmax_freq <= exac_popmax_threshold, "Exac popmax freq %s > %s" % (exac_popmax_freq, exac_popmax_threshold)
                    assert merck_wgs_3793_freq <= merck_wgs_3793_threshold


                    assert genotype.gq >= GQ_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.gq)
                    assert genotype.extras["dp"] >= DP_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.extras["dp"])
                    if genotype.num_alt == 1:
                        assert genotype.ab >= AB_threshold/100., "%s %s - AB is %s " % (variant.chr, variant.pos, genotype.ab)
                    assert genotype.filter == "pass", "%s %s - filter is %s " % (variant.chr, variant.pos, genotype.filter)

                    writer.writerow(map(str, [
                        project_id,
                        family.family_id,
                        individual.indiv_id,
                        get_gene_symbol(variant),
                        variant.chr,
                        variant.pos,
                        variant.ref,
                        variant.alt,
                        variant.vcf_id,
                        variant.annotation['vep_group'],
                        g1k_freq,
                        g1k_popmax_freq,
                        exac_freq,
                        exac_popmax_freq,
                        merck_wgs_3793_freq,
                        genotype_str,
                        genotype.num_alt,
                        genotype.ab,
                        genotype.extras["ad"],
                        genotype.extras["dp"],
                        genotype.gq,
                        genotype.extras["pl"],
                        genotype.filter,
                    ]))
                    individual_variants_f.flush()
        individual_variants_f.close()
