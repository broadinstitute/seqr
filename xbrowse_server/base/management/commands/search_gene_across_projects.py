from optparse import make_option
import sys
import os
from django.core.management.base import BaseCommand
import json
import time
import datetime
from pprint import pprint
from xbrowse_server.analysis import project as project_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference, get_project_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from django.conf import settings
from xbrowse_server.base.models import Project
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse_server import mall
import csv


class Command(BaseCommand):
    __VERSION__= '0.0.1'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*',metavar='project', help='A list of projects to search in')
        parser.add_argument('-f', '--max-af', dest='max_af', help='ExAC and 1000 genomes allele frequency threshold.', default=0.01, type=float)
        group = parser.add_argument_group('required arguments')
        group.add_argument('-g', '--gene_id', dest='gene_id', help='Searches for this gene id.', required=True)


    def handle(self, *args, **options):
      '''
        Search for a gene across a project
        Args:
       		1. Gene name (Required)- the name of the gene to search for
       		2. A list of project name to search for (Optional- if not given will search in all projects (Warn: Computationally Expensive!))

      '''
      self.search_for_gene(options['gene_id'], args, max_af=options['max_af'])
      
      
    def search_for_gene(self, search_gene_id, project_id_list, max_af=0.01):
      '''
        Search for a gene across project(s)
        Args:
          1. search_gene_id: Gene ID to search for
          2. proj_list: An optional list of projects to narrow down search to
      '''
      gene_id = get_gene_id_from_str(search_gene_id, get_reference())
      gene = get_reference().get_gene(gene_id)
      
      print("Staring gene search for: %s %s in projects: %s\n" % (search_gene_id, gene['gene_id'], ", ".join(project_id_list)))
      print("Max AF threshold: %s" % max_af)

      # all rare coding variants
      variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)
      print("All Filters: ")
      pprint(variant_filter.toJSON())

      output_filename = 'results_'+search_gene_id + '.tsv'
      outfile = open(output_filename,'w')

      header = ["project_id","gene", "chr", "pos", "ref", "alt", "rsID", "filter", "impact",
                "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
                "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
                "freq_exac_v3", "freq_exac_v3_popmax",
                "all_genotypes"]

      
      writer = csv.writer(outfile,delimiter='\t')
      writer.writerow(header)
      
      if project_id_list: 
          for project_id in project_id_list:
              project = Project.objects.filter(project_id=project_id)[0]  # TODO validate
      else:
          project_id_list = [p.project_id for p in Project.objects.all()]
      
      for project_id in project_id_list:
          project = Project.objects.filter(project_id=project_id)[0]
          if get_project_datastore(project_id).project_collection_is_loaded(project_id):
              print("Running on project %s" % project_id)
          else:
              print("Skipping project %s - gene search is not enabled for this project" % project_id)
              continue

          for variant in project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter):
              if max(variant.annotation['freqs'].values()) >= max_af:
                  continue
              #pprint(variant.toJSON())
              add_extra_info_to_variants_project(get_reference(), project, [variant])

              worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"][gene_id]
              worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
              all_genotypes_list = []
              pass_filter = "N/A"
              for indiv_id, genotype in variant.genotypes.items():
                  pass_filter = genotype.filter  # filter value is stored in the genotypes even though it's the same for all individuals
                  if genotype.num_alt > 0:
                    all_genotypes_list.append("%s[gt:%s GQ:%s AB:%0.3f]" % (indiv_id, ">".join(genotype.alleles), genotype.gq, genotype.ab if genotype.ab is not None else float('NaN')))

              measureset_id, clinvar_significance = settings.CLINVAR_VARIANTS.get(variant.unique_tuple(), ("", ""))
              row = map(str,
                  [project_id, 
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
      
          

      	 
  
        
