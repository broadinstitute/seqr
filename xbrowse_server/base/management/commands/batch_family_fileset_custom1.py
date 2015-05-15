import csv
from django.core.management.base import BaseCommand
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse.variant_search.family import get_variants_with_inheritance_mode
from xbrowse_server import mall
from xbrowse_server.base.models import Project, Family
from xbrowse_server.mall import get_mall, get_reference


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
    variant_filter.ref_freqs.append(('g1k_all', 0.01))
    variant_filter.ref_freqs.append(('exac', 0.01))
    variant_filter.ref_freqs.append(('exac-popmax', 0.01))
    #variant_filter.ref_freqs.append(('merck-wgs-3793', 0.05))
    quality_filter = {
        'filter': 'pass',
        'min_gq': 30,
        'min_ab': 15,
    }

    # run MendelianVariantSearch for each family, collect results
    family_results = {}
    for family in project.get_families():
        family_results[family] = list(get_variants_with_inheritance_mode(
            get_mall(),
            family.xfamily(),
            inheritance_mode,
            variant_filter=variant_filter,
            quality_filter=quality_filter,
            ))

    return family_results


class Command(BaseCommand):

    def handle(self, *args, **options):

        project_ids = args
        family_variants_f = open('family_variants.tsv', 'w')


        # collect the resources that we'll need here
        annotator = mall.get_annotator()
        custom_population_store = mall.get_custom_population_store()

        # create family_variants.tsv
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
            'exac_af',
            '1kg_af',
            'merck-wgs-3793',
            ]
        writer.writerow(header_fields)

        for inheritance_mode in ['homozygous_recessive', 'dominant', 'compound_het', 'de_novo', 'x_linked_recessive']:
            for project_id in project_ids:
                project = Project.objects.get(project_id=project_id)
                families = project.get_families()

                # get the variants for this inheritance / project combination
                family_results = get_variants_for_inheritance_for_project(project, inheritance_mode)

                for family in families:
                    for variant in family_results[family]:
                        custom_populations = custom_population_store.get_frequencies(variant.xpos, variant.ref, variant.alt)
                        writer.writerow([
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
                            str(variant.annotation['freqs']['exac']),
                            str(variant.annotation['freqs']['g1k_all']),
                            str(custom_populations.get('merck-wgs-3793', 0.0)),
                            ])

        family_variants_f.close()



        #
        #
        # # create variants.tsv
        # by_variant = {}
        # variant_info = {}
        # for family in families:
        #     for variant in family_results[family]:
        #         if variant.unique_tuple() not in by_variant:
        #             by_variant[variant.unique_tuple()] = set()
        #             variant_info[variant.unique_tuple()] = variant
        #         by_variant[variant.unique_tuple()].add(family.family_id)
        # f = open('variants.tsv', 'w')
        # writer = csv.writer(f, dialect='excel', delimiter='\t')
        # headers = [
        #     '#chrom',
        #     'ref',
        #     'alt',
        #     'rsid',
        #     'gene'
        #     'annotation',
        #     'num_families',
        # ]
        # headers.extend([fam.family_id for fam in families])
        # writer.writerow(headers)
        # for variant_t in sorted(variant_info.keys()):
        #     variant = variant_info[variant_t]
        #     fields = [
        #         variant.chr,
        #         variant.ref,
        #         variant.alt,
        #         variant.vcf_id,
        #         get_gene_symbol(variant_info[variant_t]),
        #         variant.annotation['vep_group'],
        #         str(len(by_variant[variant_t])),
        #     ]
        #     for family in families:
        #         fields.append('1' if family.family_id in by_variant[variant_t] else '0')
        #     writer.writerow(fields)
        # f.close()
        #
        # # create genes.tsv
        # by_gene = {}
        # for family in families:
        #     for variant in family_results[family]:
        #         gene_symbol = get_gene_symbol(variant)
        #         if gene_symbol not in by_gene:
        #             by_gene[gene_symbol] = set()
        #         by_gene[gene_symbol].add(family.family_id)
        #
        # f = open('genes.tsv', 'w')
        # writer = csv.writer(f, dialect='excel', delimiter='\t')
        # headers = [
        #     '#gene',
        #     'num_families',
        # ]
        # headers.extend([fam.family_id for fam in families])
        # writer.writerow(headers)
        # for gene_symbol in sorted(by_gene.keys()):
        #     fields = [
        #         gene_symbol,
        #         str(len(by_gene[gene_symbol])),
        #     ]
        #     for family in families:
        #         fields.append('1' if family.family_id in by_gene[gene_symbol] else '0')
        #     writer.writerow(fields)
        # f.close()
        #