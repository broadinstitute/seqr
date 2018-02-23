import csv
from django.core.management.base import BaseCommand
from xbrowse.variant_search.family import get_variants_with_inheritance_mode
from xbrowse_server.base.models import Project, Family
from xbrowse_server.mall import get_mall, get_reference


def get_gene_symbol(variant):
    gene_id = variant.annotation['vep_annotation'][variant.annotation['worst_vep_annotation_index']]['gene']
    return get_reference().get_gene_symbol(gene_id)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):

        project_id = args[0]
        inheritance_mode = args[1]
        fam_list_file_path = args[2]

        project = Project.objects.get(project_id=project_id)
        families = []
        for line in open(fam_list_file_path):
            family_id = line.strip('\n')
            families.append(Family.objects.get(project=project, family_id=family_id))


        # create search spec
        variant_filter = next(f for f in project.get_default_variant_filters() if f['slug'] == 'moderate_impact')['variant_filter']
        quality_filter = {
            'min_gq': 20,
            'min_ab': 25,
        }

        # run MendelianVariantSearch for each family, collect results
        family_results = {}
        for family in families:
            family_results[family] = list(get_variants_ith_inheritance_mode(
                get_mall(project),
                family.xfamily(),
                inheritance_mode,
                variant_filter=variant_filter,
                quality_filter=quality_filter,
            ))

        # create family_variants.tsv
        f = open('family_variants.tsv', 'w')
        writer = csv.writer(f, dialect='excel', delimiter='\t')
        writer.writerow([
            '#family_id',
            'gene',
            'chrom',
            'ref',
            'alt',
            'rsid',
            'annotation',
        ])
        for family in families:
            for variant in family_results[family]:
                writer.writerow([
                    family.family_id,
                    get_gene_symbol(variant),
                    variant.chr,
                    variant.ref,
                    variant.alt,
                    variant.vcf_id,
                    variant.annotation['vep_group'],
                ])
        f.close()

        # create variants.tsv
        by_variant = {}
        variant_info = {}
        for family in families:
            for variant in family_results[family]:
                if variant.unique_tuple() not in by_variant:
                    by_variant[variant.unique_tuple()] = set()
                    variant_info[variant.unique_tuple()] = variant
                by_variant[variant.unique_tuple()].add(family.family_id)
        f = open('variants.tsv', 'w')
        writer = csv.writer(f, dialect='excel', delimiter='\t')
        headers = [
            '#chrom',
            'ref',
            'alt',
            'rsid',
            'gene'
            'annotation',
            'num_families',
        ]
        headers.extend([fam.family_id for fam in families])
        writer.writerow(headers)
        for variant_t in sorted(variant_info.keys()):
            variant = variant_info[variant_t]
            fields = [
                variant.chr,
                variant.ref,
                variant.alt,
                variant.vcf_id,
                get_gene_symbol(variant_info[variant_t]),
                variant.annotation['vep_group'],
                str(len(by_variant[variant_t])),
            ]
            for family in families:
                fields.append('1' if family.family_id in by_variant[variant_t] else '0')
            writer.writerow(fields)
        f.close()

        # create genes.tsv
        by_gene = {}
        for family in families:
            for variant in family_results[family]:
                gene_symbol = get_gene_symbol(variant)
                if gene_symbol not in by_gene:
                    by_gene[gene_symbol] = set()
                by_gene[gene_symbol].add(family.family_id)

        f = open('genes.tsv', 'w')
        writer = csv.writer(f, dialect='excel', delimiter='\t')
        headers = [
            '#gene',
            'num_families',
        ]
        headers.extend([fam.family_id for fam in families])
        writer.writerow(headers)
        for gene_symbol in sorted(by_gene.keys()):
            fields = [
                gene_symbol,
                str(len(by_gene[gene_symbol])),
            ]
            for family in families:
                fields.append('1' if family.family_id in by_gene[gene_symbol] else '0')
            writer.writerow(fields)
        f.close()

