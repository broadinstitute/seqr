import csv
import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter, VariantFilter
from xbrowse.reference.clinvar import get_clinvar_variants
from xbrowse.variant_search.family import get_variants_with_inheritance_mode, get_variants
from xbrowse_server import mall
from xbrowse_server.base.models import Project, Family
from xbrowse_server.mall import get_mall, get_reference, get_datastore
from xbrowse.annotation.vep_annotations import SO_SEVERITY_ORDER


AB_threshold = 25
GQ_threshold = 20
DP_threshold = 10
g1k_freq_threshold = 0.01
g1k_popmax_freq_threshold = 0.01
exac_freq_threshold = 0.01
exac_popmax_threshold = 0.01
merck_wgs_3793_threshold = 1 # 0.05
merck_wgs_144_threshold = 1  # 0.05


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
    #variant_filter = VariantFilter(so_annotations=SO_SEVERITY_ORDER, ref_freqs=[])
    variant_filter = get_default_variant_filter('moderate_impact')
    variant_filter.ref_freqs.append(('1kg_wgs_phase3', g1k_freq_threshold))
    variant_filter.ref_freqs.append(('1kg_wgs_phase3_popmax', g1k_popmax_freq_threshold))
    variant_filter.ref_freqs.append(('exac_v3', exac_freq_threshold))
    variant_filter.ref_freqs.append(('exac_v3_popmax', exac_popmax_threshold))
    variant_filter.ref_freqs.append(('merck-wgs-3793', merck_wgs_3793_threshold))
    #variant_filter.ref_freqs.append(('merck-pcr-free-wgs-144', merck_wgs_144_threshold))
    quality_filter = {
#        'vcf_filter': 'pass',
        'min_gq': GQ_threshold,
        'min_ab': AB_threshold,
    }

    # run MendelianVariantSearch for each family, collect results

    families = project.get_families()

    for i, family in enumerate(families):
        print("Processing %s - family %s  (%d / %d)" % (inheritance_mode, family.family_id, i+1, len(families)))
        try:
            if inheritance_mode == "all_variants":
                yield family, list(get_variants(
                        get_datastore(project),
                        family.xfamily(),
                        variant_filter=variant_filter,
                        quality_filter=quality_filter,
                        indivs_to_consider=family.indiv_id_list()
                        ))
            else:
                yield family, list(get_variants_with_inheritance_mode(
                        get_mall(project),
                        family.xfamily(),
                        inheritance_mode,
                        variant_filter=variant_filter,
                        quality_filter=quality_filter,
                        ))
        except ValueError as e:
            print("Error: %s. Skipping family %s" % (str(e), str(family)))

def handle_project(project_id):
        filename = 'family_variants_%s.tsv.gz' % project_id
        print("Generating report: " + filename)

        # create family_variants.tsv
        family_variants_f = gzip.open(filename, 'w')
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
            'filter', 
            'clinvar_status',
            'annotation',
            '1kg_af',
            '1kg_popmax_af',
            'exac_af',
            'exac_popmax_af',
            'merck_wgs_3793_af',
            'merck_wgs_144_af',
            'multiallelic_site_alt_alleles (* = spanning deletion)',
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

        for inheritance_mode in ['homozygous_recessive', 'dominant', 'compound_het', 'de_novo', 'x_linked_recessive', 'all_variants']:
            # collect the resources that we'll need here
            annotator = mall.get_annotator()
            custom_population_store = mall.get_custom_population_store()

            project = Project.objects.get(project_id=project_id)

            # get the variants for this inheritance / project combination
            for i, (family, family_results) in enumerate(get_variants_for_inheritance_for_project(project, inheritance_mode)):
                for variant in family_results:
                    custom_populations = custom_population_store.get_frequencies(variant.xpos, variant.ref, variant.alt)
                    g1k_freq = variant.annotation['freqs']['1kg_wgs_phase3']
                    g1k_popmax_freq = variant.annotation['freqs']['1kg_wgs_phase3_popmax']
                    exac_freq = variant.annotation['freqs']['exac_v3']
                    exac_popmax_freq =  variant.annotation['freqs']['exac_v3_popmax']
                    merck_wgs_3793_freq = custom_populations.get('merck-wgs-3793', 0.0)
                    merck_wgs_144_freq = custom_populations.get('merck-pcr-free-wgs-144', 0.0)

                    try:
                        assert g1k_freq <= g1k_freq_threshold, "g1k freq %s > %s" % (g1k_freq, g1k_freq_threshold)
                        assert g1k_popmax_freq <= g1k_popmax_freq_threshold, "g1k freq %s > %s" % (g1k_popmax_freq, g1k_popmax_freq_threshold)
                        assert exac_freq <= exac_freq_threshold, "Exac freq %s > %s" % (exac_freq, exac_freq_threshold)
                        assert exac_popmax_freq <= exac_popmax_threshold, "Exac popmax freq %s > %s" % (exac_popmax_freq, exac_popmax_threshold)
                        #assert merck_wgs_3793_freq <= merck_wgs_3793_threshold, "Merck WGS 3793 threshold %s > %s" % (merck_wgs_3793_freq, merck_wgs_3793_threshold)
                        #assert merck_wgs_144_freq <= merck_wgs_144_threshold, "Merck PCR free 144 threshold %s > %s" % (merck_wgs_144_freq, merck_wgs_144_threshold)
                    except AssertionError as e:
                        import traceback
                        traceback.print_exc()

                    # filter value is stored in the genotypes
                    if len(family.get_individuals()) == 0:
                        print("Family has 0 individuals: %s - skipping..." % str(family))
                        continue
                    
                    genotype = variant.get_genotype(family.get_individuals()[0].indiv_id) 
                    if genotype is not None:
                        filter_value = genotype.filter
                    else:
                        filter_value = 'unknown'

                    multiallelic_site_other_alleles = []
                    if len(variant.extras['orig_alt_alleles']) > 1:
                        multiallelic_site_other_alleles = variant.extras['orig_alt_alleles']

                    clinvar_significance = get_clinvar_variants().get(variant.unique_tuple(), [""])[-1]
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
                        filter_value,
                        clinvar_significance,
                        variant.annotation['vep_group'],

                        g1k_freq,
                        g1k_popmax_freq,

                        exac_freq,
                        exac_popmax_freq,
                        merck_wgs_3793_freq,
                        merck_wgs_144_freq,
                        ", ".join(multiallelic_site_other_alleles),
                        '',
                    ]

                    for i, individual in enumerate(family.get_individuals()):
                        if i >= 10:
                            break

                        genotype = variant.get_genotype(individual.indiv_id)

                        if genotype is None:
                            row.extend([individual.indiv_id, "./.", "", "", "", "", "", ""])
                            continue
                        else:
                            #assert genotype.filter == "pass", "%s %s - filter is %s " % (variant.chr, variant.pos, genotype.filter)
                            try:
                                assert genotype.gq >= GQ_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.gq)
                                assert genotype.extras["dp"] >= DP_threshold, "%s %s - GQ is %s " % (variant.chr, variant.pos, genotype.extras["dp"])
                                if genotype.num_alt == 1:
                                    assert genotype.ab is None or genotype.ab >= AB_threshold/100., "%s %s - AB is %s " % (variant.chr, variant.pos, genotype.ab)
                            except AssertionError as e:
                                import traceback
                                traceback.print_exc()

                            genotype_str = "/".join(genotype.alleles) if genotype.alleles else "./."

                            row.extend([
                                    individual.indiv_id,
                                    genotype_str,
                                    genotype.num_alt,
                                    genotype.ab if genotype.ab is not None else '',
                                    genotype.extras["ad"],
                                    genotype.extras["dp"],
                                    genotype.gq,
                                    genotype.extras["pl"],
                            ])

                    writer.writerow(row)
                    family_variants_f.flush()

        family_variants_f.close()
        print("Done with " + filename)



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if not args:
            sys.exit("ERROR: please specify project id on the command line")

        print("Project ids: " + str(args))
        for project_id in args:
            handle_project(project_id)
            print("----------")

