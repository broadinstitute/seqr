import csv
import gzip
import sys
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
    variant_filter.ref_freqs.append(('merck-wgs-3793', 0.05))
    quality_filter = {
        'filter': 'pass',
        'min_gq': 30,
        'min_ab': 15,
    }

    # run MendelianVariantSearch for each family, collect results
    family_results = {}
    families = project.get_families()
    for i, family in enumerate(families):
        print("Processing %s - family %s  (%d / %d)" % (inheritance_mode, family.family_id, i+1, len(families)))
        family_results[family] = list(get_variants_with_inheritance_mode(
            get_mall(project.project_id),
            family.xfamily(),
            inheritance_mode,
            variant_filter=variant_filter,
            quality_filter=quality_filter,
            ))

    return family_results


class Command(BaseCommand):

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
            'exac_af',
            '1kg_af',
            'exac_popmax_af',
            'merck_wgs_3793_af',
            ]
        writer.writerow(header_fields)
        for inheritance_mode in ['homozygous_recessive', 'dominant', 'compound_het', 'de_novo', 'x_linked_recessive']:
            # collect the resources that we'll need here
            annotator = mall.get_annotator()
            custom_population_store = mall.get_custom_population_store()

            project = Project.objects.get(project_id=project_id)
            families = project.get_families()

            # get the variants for this inheritance / project combination
            family_results = get_variants_for_inheritance_for_project(project, inheritance_mode)

            for i, family in enumerate(families):
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
                        str(custom_populations.get('exac-popmax', 0.0)),
                        str(custom_populations.get('merck-wgs-3793', 0.0)),
                    ])

        family_variants_f.close()

