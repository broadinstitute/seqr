from django.core.management.base import BaseCommand

from pprint import pprint

from django.db.models.query_utils import Q
from xbrowse import genomeloc
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from xbrowse_server.analysis import project as project_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.mall import get_reference, get_project_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from django.conf import settings
from xbrowse_server.base.models import Project, Individual
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse_server import mall
import csv
import re

class Command(BaseCommand):
    __VERSION__= '0.0.1'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*',metavar='project', help='A list of projects to search in')
        #parser.add_argument('-f', '--max-af', dest='max_af', help='ExAC and 1000 genomes allele frequency threshold.', default=0.01, type=float)
        parser.add_argument('-e', '--exclude', dest='exclude_projects', help='Projects to exclude.', action="append")
        parser.add_argument('-k', '--knockouts', dest='knockouts', help='Only return knockouts.', action="store_true")
        parser.add_argument('--in-clinvar', help='only return variants that are in clinvar', action="store_true")
        parser.add_argument('-nc', '--include-non-coding', help="include non-coding variants", action="store_true")
        
        parser.add_argument('-o', '--output-filename')
        group = parser.add_argument_group('required arguments')
        group.add_argument('-g', '--gene-id', dest='gene_id', help='Searches for this gene id.', action="append")
        group.add_argument('-gl', '--gene-list', dest='gene_list', help='Searches all genes in this gene list.', action="append")
        group.add_argument('-vi', '--variant-id', dest='variant_id', help='Searches for this variant (X-12345-A-T) or position (X-12345)', action="append")

    def handle(self, *args, **options):
        gene_or_variant_ids = []
        if options['variant_id']:
            gene_or_variant_ids = options['variant_id']
            output_filename = options['output_filename'] or ('results_%s.tsv' % ".".join(gene_or_variant_ids))

        if options['gene_id']:
            gene_or_variant_ids = options['gene_id']
            output_filename = options['output_filename'] or ('results_%s.tsv' % ".".join(gene_or_variant_ids))

        if options['gene_list']:
            gene_lists = options['gene_list']
            for gene_list in gene_lists:
                matching_gene_lists = GeneList.objects.filter(Q(slug__icontains=gene_list) | Q(name__icontains=gene_list))
                if not matching_gene_lists:
                    raise ValueError("'%s' gene list not found" % gene_list)
                if len(matching_gene_lists) > 1:
                    raise ValueError("matched multiple gene lists: %s" % ", ".join([l.slug for l in matching_gene_lists]))
                
                gene_or_variant_ids.extend([i.gene_id for i in GeneListItem.objects.filter(gene_list=matching_gene_lists[0])])

            output_filename = 'results_%s.tsv' % ".".join([gene_list for gene_list in gene_lists])
        if not gene_or_variant_ids:
            raise ValueError("Must specifcy either -g or -gl or -vi arg")

        project_id_list = args
        if not project_id_list:
            project_id_list = [project.project_id for project in Project.objects.all()]

        if options['exclude_projects']:
            project_id_list = [i for i in project_id_list if i.lower() not in options['exclude_projects']]

        self.search_for_genes(gene_or_variant_ids, project_id_list, output_filename, knockouts=options['knockouts'], in_clinvar_only = options["in_clinvar"], include_non_coding=options["include_non_coding"])

    def search_for_genes(self, gene_or_variant_ids, project_id_list, output_filename, max_af=0.01, knockouts=False, in_clinvar_only=False, include_non_coding=False):
        """
        Search for a gene across project(s)

        Args:
            gene_or_variant_ids (list): 'ENSG..' gene id strings.
            project_id_list (list): (optional) project ids to narrow down the search
            output_filename (string): output file name
            max_af (float): AF filter
            in_clinvar_only (bool):
            include_non_coding (bool):
        """

        projects = [Project.objects.get(project_id=project_id) for project_id in project_id_list]

        outfile = open(output_filename, 'w')

        header = [
            "project_id", "gene", "chr", "pos", "ref", "alt", "rsID", "filter", "impact",
            "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
            "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
            "freq_exac_v3", "freq_exac_v3_popmax",  "gnomad-exomes", "gnomad-genomes", 
            "families", "all_genotypes"]

        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(header)

        # all rare coding variants
        if not knockouts:
            variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)
            #variant_filter.set_max_AF(max_af)
            if include_non_coding:
                variant_filter.so_annotations=[]
            print("All Filters: ")
            pprint(variant_filter.toJSON())

        #print("Max AF threshold: %s" % max_af)
        print("Starting search for:\n%s\nin projects:\n%s\n" % (", ".join(gene_or_variant_ids), ", ".join([p.project_id for p in projects])))

        for project in projects:
            project_id = project.project_id
            if get_project_datastore(project).project_collection_is_loaded(project):
                print("=====================")
                print("Searching project %s" % project_id)
            else:
                print("Skipping project %s - gene search is not enabled for this project" % project_id)
                continue

            indiv_cache = {}
            for gene_or_variant_id in gene_or_variant_ids:
                chrom_pos_match = re.match("([0-9XY]{1,2})-([0-9]{1,9})", gene_or_variant_id)
                chrom_pos_ref_alt_match = re.match("([0-9XY]{1,2})-([0-9]{1,9})-([ACTG])-([ACTG])", gene_or_variant_id)

                if chrom_pos_match or chrom_pos_ref_alt_match:
                    chrom = chrom_pos_match.group(1)
                    pos = int(chrom_pos_match.group(2))
                    xpos = genomeloc.get_xpos(chrom, pos)
                    ref = alt = None
                    if chrom_pos_ref_alt_match:
                        ref = chrom_pos_ref_alt_match.group(3)
                        alt = chrom_pos_ref_alt_match.group(4)
                        
                    variant = get_project_datastore(project).get_single_variant(project.project_id, None, xpos, ref, alt)
                    if variant is None:
                        continue
                    variants = [variant]
                    print("-- searching %s for variant %s-%s-%s: found %s" % (project_id, xpos, ref, alt, variant))
                    worst_annotation_idx = variant.annotation['worst_vep_annotation_index']
                    print(variant.annotation["vep_annotation"][worst_annotation_idx])
                    gene_id = variant.annotation["vep_annotation"][worst_annotation_idx]['gene_id']
                    gene = get_reference().get_gene(gene_id)
                else:
                    gene_id = get_gene_id_from_str(gene_or_variant_id, get_reference())
                    gene = get_reference().get_gene(gene_id)
                    print("-- searching %s for gene %s (%s)" % (project_id, gene["symbol"], gene_id))

                    if knockouts:
                        knockout_ids, variation = project_analysis.get_knockouts_in_gene(project, gene_id)
                        variants = variation.get_relevant_variants_for_indiv_ids(knockout_ids)
                    else:
                        variants = project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter)

                for variant in variants:
                    if not chrom_pos_match and not chrom_pos_ref_alt_match and max(variant.annotation['freqs'].values()) >= max_af:
                        continue

                    add_extra_info_to_variants_project(get_reference(), project, [variant])
                    worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"].get(gene_id)

                    if worst_annotation_idx is not None:
                        worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx] 
                    else:
                        worst_annotation = None
                    all_genotypes_list = []
                    pass_filter = "N/A"
                    family_ids = set()
                    for indiv_id, genotype in variant.genotypes.items():
                        if indiv_id in indiv_cache:
                            individual = indiv_cache[indiv_id]
                            if individual == 'deleted':
                                continue
                        else:
                            try:
                                individual = Individual.objects.get(project=project, indiv_id=indiv_id)
                                indiv_cache[indiv_id] = individual
                            except ObjectDoesNotExist:
                                # this can happen when an individual is deleted from the project - from postgres, but not from mong
                                indiv_cache[indiv_id] = 'deleted'
                                continue
                            except MultipleObjectsReturned:
                                # when several families have an individual with the same id
                                individuals = Individual.objects.filter(project=project, indiv_id=indiv_id)
                                individual = individuals[0]
                                indiv_cache[indiv_id] = individual

                        pass_filter = genotype.filter  # filter value is stored in the genotypes even though it's the same for all individuals
                        if genotype.num_alt > 0:
                            family_ids.add(individual.family.family_id)
                            all_genotypes_list.append("%s/%s%s[gt:%s GQ:%s AB:%0.3f]" % (
                                individual.family.family_id,
                                indiv_id,
                                "[Affected]" if individual.affected == "A" else ("[-]" if individual.affected == "N" else "[?]"),
                                ">".join(genotype.alleles),
                                genotype.gq,
                                genotype.ab if genotype.ab is not None else float('NaN')
                            ))

                    if len(all_genotypes_list) == 0:
                        continue

                    measureset_id, clinvar_significance = get_reference().get_clinvar_info(*variant.unique_tuple())
                    if in_clinvar_only and (not clinvar_significance or "path" not in clinvar_significance.lower()):
                        continue

                        
                    row = map(str, [
                             project_id,
                             gene,
                             variant.chr,
                             variant.pos,
                             variant.ref,
                             variant.alt,
                             variant.vcf_id or "",
                             pass_filter,
                             variant.annotation.get("vep_consequence", ""),
                             worst_annotation.get("hgvsc", "") if worst_annotation else "",
                             (worst_annotation.get("hgvsp", "") or "").replace("%3D", "=") if worst_annotation else "",
                             worst_annotation.get("sift", "") if worst_annotation else "",
                             worst_annotation.get("polyphen", "") if worst_annotation else "",
                             worst_annotation.get("mutationtaster_pred", "") if worst_annotation else "",
                             ";".join(set(worst_annotation.get("fathmm_pred", "").split('%3B'))) if worst_annotation else "",
                             measureset_id,
                             clinvar_significance,
                             variant.annotation["freqs"].get("1kg_wgs_phase3", ""),
                             variant.annotation["freqs"].get("1kg_wgs_phase3_popmax", ""),
                             variant.annotation["freqs"].get("exac_v3", ""),
                             variant.annotation["freqs"].get("exac_v3_popmax", ""),
                             variant.annotation["freqs"].get("gnomad-exomes2", ""),
                             variant.annotation["freqs"].get("gnomad-genomes2", ""),
                             ", ".join(sorted(list(family_ids))),
                             ", ".join(all_genotypes_list),
                        ])

                    writer.writerow(row)

        outfile.close()
        print("Wrote out %s" % output_filename)


