import csv
import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse.variant_search.family import get_variants_with_inheritance_mode
from xbrowse_server import mall
from xbrowse_server.base.models import Project, Family
from xbrowse_server.mall import get_mall, get_reference


AB_threshold = 15
GQ_threshold = 20
DP_threshold = 10
g1k_freq_threshold = 0.01
g1k_popmax_freq_threshold = 0.01
exac_freq_threshold = 0.01
exac_popmax_threshold = 0.01

AB_threshold = 0
GQ_threshold = 0
DP_threshold = 0
g1k_freq_threshold = 0.005
g1k_popmax_freq_threshold = 0.005
exac_freq_threshold = 0.005
exac_popmax_threshold = 0.005


def get_gene_symbol(variant):
    gene_id = variant.annotation['vep_annotation'][
        variant.annotation['worst_vep_annotation_index']]['gene']
    return get_reference().get_gene_symbol(gene_id)


def get_variants_for_inheritance_for_project(project, inheritance_mode):
    """
    Get the variants for this project / inheritance combo
    Return dict of family -> list of variants
    """

    # create search specification
    # this could theoretically differ by project, if there are different reference populations
    variant_filter = get_default_variant_filter('moderate_impact')
    variant_filter.ref_freqs.append(('1kg_wgs_phase3', g1k_freq_threshold))
    variant_filter.ref_freqs.append(('1kg_wgs_phase3_popmax', g1k_popmax_freq_threshold))
    variant_filter.ref_freqs.append(('exac_v3', exac_freq_threshold))
    variant_filter.ref_freqs.append(('exac_v3_popmax', exac_popmax_threshold))
    quality_filter = {
        'vcf_filter': 'pass',
        'min_gq': GQ_threshold,
        'min_ab': AB_threshold,
    }

    # run MendelianVariantSearch for each family, collect results
    families = project.get_families()
    for i, family in enumerate(families):
        sys.stdout.write("Processing %s - family %s  (%d / %d) .." % (inheritance_mode, family.family_id, i+1, len(families)))
        variant_list = list(get_variants_with_inheritance_mode(
            get_mall(project),
            family.xfamily(),
            inheritance_mode,
            variant_filter=variant_filter,
            quality_filter=quality_filter,
            ))
        yield family, variant_list
        print(" got %d variants" % len(variant_list))


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')


    def handle(self, *args, **options):
        if not args:
            sys.exit("ERROR: please specify project id on the command line")
        if len(args) > 1:
            sys.exit("ERROR: too many args: %s. Only one project id should be provided." % " ".join(args) )

        project_id = args[0]


        # create family_variants.tsv
        family_variants_f = gzip.open('family_variants_%s.tsv.gz' % project_id, 'w')
        writer = csv.writer(family_variants_f, dialect='excel', delimiter='\t')

        header_fields = [
            '#inheritance_mode',
            'project_id',
            'family_id',
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
            '',
            ]

        genotype_headers = [
            'sample_id',
            'str',
            'num_alt',
            'allele_balance',
            'AD',
            'DP',
            'GQ',
            'PL',
        ]

        for i in range(0, 10):
            for h in genotype_headers:
                header_fields.append("genotype%d_%s" % (i, h))

        writer.writerow(header_fields)
        family_variants_f.flush()

        for inheritance_mode in ['dominant', 'homozygous_recessive', 'compound_het', 'de_novo', 'x_linked_recessive']:
            # collect the resources that we'll need here
            annotator = mall.get_annotator()
            custom_population_store = mall.get_custom_population_store()

            project = Project.objects.get(project_id=project_id)
            families = project.get_families()

            # get the variants for this inheritance / project combination
            for i, (family, variant_list) in enumerate(get_variants_for_inheritance_for_project(project, inheritance_mode)):
                for variant in variant_list:
                    #if variant.annotation['vep_group'] != "missense":
                    #    continue
                    custom_populations = custom_population_store.get_frequencies(variant.xpos, variant.ref, variant.alt)
                    g1k_freq = variant.annotation['freqs']['1kg_wgs_phase3']
                    g1k_popmax_freq = variant.annotation['freqs']['1kg_wgs_phase3_popmax']
                    exac_freq = variant.annotation['freqs']['exac_v3']
                    exac_popmax_freq =  variant.annotation['freqs']['exac_v3_popmax']

                    assert g1k_freq <= g1k_freq_threshold, "g1k freq %s > %s" % (g1k_freq, g1k_freq_threshold)
                    assert g1k_popmax_freq <= g1k_popmax_freq_threshold, "g1k freq %s > %s" % (g1k_popmax_freq, g1k_popmax_freq_threshold)
                    assert exac_freq <= exac_freq_threshold, "Exac freq %s > %s" % (exac_freq, exac_freq_threshold)
                    assert exac_popmax_freq <= exac_popmax_threshold, "Exac popmax freq %s > %s" % (exac_popmax_freq, exac_popmax_threshold)


                    row = [
                        inheritance_mode,
                        project_id,
                        family.family_id,
                        get_gene_symbol(variant),
                        variant.chr,
                        str(variant.pos),
                        variant.ref,
                        variant.alt,
                        variant.vcf_id,
                        variant.annotation['vep_group'],

                        g1k_freq,
                        g1k_popmax_freq,

                        exac_freq,
                        exac_popmax_freq,
                        '',
                    ]

                    for i, individual in enumerate(family.get_individuals()):
                        if i >= 10:
                            break

                        genotype = variant.get_genotype(individual.indiv_id)
                        if genotype is None:
                            print("WARNING: %s-%s-%s-%s variant genotype for %s is None" % (variant.chr, variant.pos, variant.ref, variant.alt, individual.indiv_id))
                            continue

                        assert genotype.filter == "pass", "%s %s - filter is %s " % (variant.chr, variant.pos, genotype.filter)
                        assert (not genotype.gq) or genotype.gq >= GQ_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.gq)
                        assert (not genotype.extras["dp"]) or genotype.extras["dp"] >= DP_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.extras["dp"])
                        if genotype.num_alt == 1:
                            assert (not genotype.ab) or genotype.ab >= AB_threshold/100., "%s %s - AB is %s " % (variant.chr, variant.pos, genotype.ab)

                        genotype_str = "/".join(genotype.alleles) if genotype.alleles else "./."

                        row.extend([
                            individual.indiv_id,
                            genotype_str,
                            genotype.num_alt,
                            genotype.ab,
                            genotype.extras["ad"],
                            genotype.extras["dp"],
                            genotype.gq,
                            genotype.extras["pl"],])

                    writer.writerow(row)
                    family_variants_f.flush()

        family_variants_f.close()

