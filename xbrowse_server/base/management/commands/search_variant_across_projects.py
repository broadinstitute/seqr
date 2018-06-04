from django.core.management.base import BaseCommand, CommandError

from pprint import pprint, pformat

from django.db.models.query_utils import Q

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import logging
from xbrowse.core.genomeloc import get_xpos
from xbrowse_server.analysis import project as project_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.mall import get_reference, get_project_datastore, get_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from django.conf import settings
from xbrowse_server.base.models import Project, Individual
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse_server import mall
import csv


class Command(BaseCommand):
    __VERSION__= '0.0.1'

    def add_arguments(self, parser):
        group = parser.add_argument_group('required arguments')
        #group.add_argument('-va', '--variant', nargs="+", help='Variant chromosome and position (eg. X-12345-A-G)')
        parser.add_argument('-e', '--exclude', dest='exclude_projects', help='Projects to exclude.', action="append")
        parser.add_argument('args', nargs='*', metavar="projects", help='One or more projects to search in. If not specified, all projects will be searched.')

    def handle(self, *args, **options):
        # check that variants can be parsed
        #variants = []
        #for variant in options['variant']:
        #    try:
        ##        chrom, pos, ref, alt = variant.split("-")
        #       get_xpos(chrom, int(pos))
        #    except Exception as e:
        #        raise CommandError("Couldn't parse variant: '%s': %s" % (variant, e))
        #    else:
        #        variants.append(variant)

        project_id_list = args
        if not project_id_list:
            project_id_list = [project.project_id for project in Project.objects.all()]

        if options['exclude_projects']:
            project_id_list = [i for i in project_id_list if i.lower() not in options['exclude_projects']]

        variants = [
                #(get_xpos("2", 179514069), "A", "C"),
                #(get_xpos("2", 179585312), "G", "A"),
                #(get_xpos("2", 179486223), "C", "T"),
                #(get_xpos("2", 179440163), "C", "G"),  # 179514069
            (get_xpos("2", 178649342), "A", "C"),
            (get_xpos("2", 178720585), "G", "A"),
            (get_xpos("2", 178621496), "C", "T"),
            (get_xpos("2", 178575436), "C", "G"),  # 179514069
        ]

        #output_filename = 'results_%s.tsv' % "_".join(variants)

        self.search_for_variants(variants, project_id_list, output_filename="results.tsv")

    def search_for_variants(self, variants, project_id_list, output_filename):
        """
        Search for a variants in one more project(s)

        Args:
            variants (list): variant list
            project_id_list (list): (optional) project ids to narrow down the search
            output_filename (string): output file name
        """

        projects = [Project.objects.get(project_id=project_id) for project_id in project_id_list]

        outfile = open(output_filename, 'w')

        header = [
            "project_id", "chr", "pos", "ref", "alt", "rsID", "filter", "impact",
            "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
            "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
            "freq_exac_v3", "freq_exac_v3_popmax",  "gnomad-exomes", "gnomad-genomes", 
            "families", "all_genotypes"]

        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(header)

        # all rare coding variants
        for project in projects:
            project_id = project.project_id
            if not project.has_elasticsearch_index():
                continue

            print(project_id)
            for family in project.family_set.all():
                found_variants = []
                for i, variant in enumerate(variants):
                    #chrom, pos, ref, alt = variant.split("-")
                    #xpos = get_xpos(chrom, int(pos))
                    xpos, ref, alt = variant

                    try:
                        found_variant = get_datastore(project).get_single_variant(project.project_id, family.family_id, xpos, ref, alt)
                    except Exception as e:
                        logging.info("Search failed: " + str(e))
                        found_variant = None

                    if not found_variant:
                        break

                    add_extra_info_to_variants_project(get_reference(), project, [found_variant])

                    found_variants.append(found_variant)
                else:
                    for found_variant in found_variants:
                        print(str(found_variant) + " found in project '%s' family '%s': %s" % (project_id, family, ", ".join(["%s: %s" % (k, v.get("num_alt")) for k, v in found_variant.toJSON()["genotypes"].items()])))
                    print("====================")
                    print("====================")

        return
"""
                    worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"].values()[0]
                    worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
                    all_genotypes_list = []
                    pass_filter = "N/A"
                    family_ids = set()

                    for indiv_id, genotype in variant.genotypes.items():
                        try:
                            individual = Individual.objects.get(project=project, indiv_id=indiv_id)
                        except ObjectDoesNotExist:
                            # this can happen when an individual is deleted from the project - from postgres, but not from mong
                            continue
                        except MultipleObjectsReturned:
                            # when several families have an individual with the same id
                            individuals = Individual.objects.filter(project=project, indiv_id=indiv_id)
                            individual = individuals[0]

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
                    row = map(str, [
                        project_id,
                             worst_annotation.get("symbol"),
                             variant.chr,
                             variant.pos,
                             variant.ref,
                             variant.alt,
                             variant.vcf_id or "",
                             pass_filter,
                             variant.annotation.get("vep_consequence", ""),
                             worst_annotation.get("hgvsc", ""),
                             (worst_annotation.get("hgvsp", "") or "").replace("%3D", "="),
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
                             variant.annotation["freqs"].get("gnomad-exomes2", ""),
                             variant.annotation["freqs"].get("gnomad-genomes2", ""),
                             ", ".join(sorted(list(family_ids))),
                             ", ".join(all_genotypes_list),
                        ])

                    writer.writerow(row)

                outfile.close()
                print("Wrote out %s" % output_filename)
"""