from django.core.management.base import BaseCommand

from pprint import pprint

from django.db.models.query_utils import Q

from xbrowse.reference.clinvar import get_clinvar_variants
from xbrowse_server.analysis import project as project_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.mall import get_reference, get_project_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from django.conf import settings
from xbrowse_server.base.models import Project, Individual
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse_server import mall
import csv


class Command(BaseCommand):
    __VERSION__= '0.0.1'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*',metavar='project', help='A list of projects to search in')
        parser.add_argument('-f', '--max-af', dest='max_af', help='ExAC and 1000 genomes allele frequency threshold.', default=0.01, type=float)
        group = parser.add_argument_group('required arguments')
        group.add_argument('-g', '--gene_id', dest='gene_id', help='Searches for this gene id.')
        group.add_argument('-gl', '--gene_list', dest='gene_list', help='Searches all genes in this gene list.', action="append")

    def handle(self, *args, **options):
        if options['gene_id']:
            gene_id = options['gene_id']
            gene_ids = [gene_id]
            output_filename = 'results_%s.tsv' % gene_id
        elif options['gene_list']:
            gene_lists = options['gene_list']
            gene_ids = []
            for gene_list in gene_lists:
                matching_gene_lists = GeneList.objects.filter(Q(slug__icontains=gene_list) | Q(name__icontains=gene_list))
                if not matching_gene_lists:
                    raise ValueError("'%s' gene list not found" % gene_list)
                if len(matching_gene_lists) > 1:
                    raise ValueError("matched multiple gene lists: %s" % ", ".join([l.slug for l in matching_gene_lists]))
                
                gene_ids.extend([i.gene_id for i in GeneListItem.objects.filter(gene_list=matching_gene_lists[0])])

            output_filename = 'results_%s.tsv' % ".".join([gene_list for gene_list in gene_lists])
        else:
            raise ValueError("Must specifcy either -g or -gl arg")

        self.search_for_genes(gene_ids, args, output_filename, max_af=options['max_af'])

    def search_for_genes(self, gene_ids, project_id_list, output_filename, max_af=0.01):
        """
        Search for a gene across project(s)

        Args:
            gene_ids (list): 'ENSG..' gene id strings.
            project_id_list (list): (optional) project ids to narrow down the search
            output_filename (string): output file name
            max_af (float): AF filter
        """

        outfile = open(output_filename, 'w')

        header = ["project_id","gene", "chr", "pos", "ref", "alt", "rsID", "filter", "impact",
                "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
                "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
                "freq_exac_v3", "freq_exac_v3_popmax",
                "all_genotypes"]

        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(header)

        print("Staring gene search for:\n  %s\n  in projects: %s\n" % (", ".join(gene_ids), ", ".join(project_id_list)))
        print("Max AF threshold: %s" % max_af)

        # all rare coding variants
        variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)
        print("All Filters: ")
        pprint(variant_filter.toJSON())

        if project_id_list:
            projects = [Project.objects.get(project_id=project_id) for project_id in project_id_list]
        else:
            projects = Project.objects.all()

        indiv_id_cache = {}
        for project in projects:
            project_id = project.project_id

            for gene_id in gene_ids:
                gene_id = get_gene_id_from_str(gene_id, get_reference())

                gene = get_reference().get_gene(gene_id)

                if get_project_datastore(project_id).project_collection_is_loaded(project_id):
                    print("Running on project %s" % project_id)
                else:
                    print("Skipping project %s - gene search is not enabled for this project" % project_id)
                    continue

                for variant in project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter):
                    if max(variant.annotation['freqs'].values()) >= max_af:
                        continue

                    add_extra_info_to_variants_project(get_reference(), project, [variant])

                    worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"][gene_id]
                    worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
                    all_genotypes_list = []
                    pass_filter = "N/A"
                    for indiv_id, genotype in variant.genotypes.items():
                        individual = indiv_id_cache.get('indiv_id')
                        if individual is None:
                            individual = Individual.objects.get(project=project, indiv_id=indiv_id)
                            indiv_id_cache[indiv_id] = individual

                        pass_filter = genotype.filter  # filter value is stored in the genotypes even though it's the same for all individuals
                        if genotype.num_alt > 0:
                            all_genotypes_list.append("%s%s[gt:%s GQ:%s AB:%0.3f]" % (
                                indiv_id,
                                "[Affected]" if individual.affected == "A" else ("[-]" if individual.affected == "N" else "[?]"),
                                ">".join(genotype.alleles),
                                genotype.gq,
                                genotype.ab if genotype.ab is not None else float('NaN')
                            ))

                    measureset_id, clinvar_significance = get_clinvar_variants().get(variant.unique_tuple(), ("", ""))
                    row = map(str, [
                        project_id,
                             gene["symbol"],
                             variant.chr,
                             variant.pos,
                             variant.ref,
                             variant.alt,
                             variant.vcf_id or "",
                             pass_filter,
                             variant.annotation.get("vep_consequence", ""),
                             worst_annotation.get("hgvsc", ""),
                             worst_annotation.get("hgvsp", "").replace("%3D", "="),
                             worst_annotation.get("sift", ""),
                             worst_annotation.get("polyphen", ""),
                             worst_annotation.get("mutationtaster_pred", ""),
                             ";".join(set(worst_annotation.get("fathmm_pred", "").split('%3B'))),
                             measureset_id,
                             clinvar_significance,
                             variant.annotation["freqs"].get("1kg_wgs_phase3", ""),
                             variant.annotation["freqs"].get("1kg_wgs_phase3_popmax", ""),
                             variant.annotation["freqs"].get("exac_v3", ""),
                             variant.annotation["freqs"].get("exac_v3_popmax", ""),
                             ", ".join(all_genotypes_list),
                        ])
                    writer.writerow(row)

        outfile.close()
        print("Wrote out %s" % output_filename)
