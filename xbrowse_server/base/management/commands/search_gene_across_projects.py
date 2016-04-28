from optparse import make_option
import sys
import os
from django.core.management.base import BaseCommand
from xbrowse_server.reports.utilities import fetch_project_individuals_data
import json
import time
import datetime
from xbrowse_server.analysis import project as project_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
from xbrowse_server.analysis.project import get_knockouts_in_gene
from django.conf import settings
from xbrowse_server.base.models import Project
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse_server import mall
import csv


class Command(BaseCommand):
    __VERSION__= '0.0.1'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+',metavar='project', help='A list of projects to search in')
        group = parser.add_argument_group('required arguments')
        group.add_argument('--gene_id',
                           '-g',
                    dest='gene_id',
                    help='Searches for this gene id.',
                    required=True
                    )
		


    def handle(self, *args, **options):
      '''
        Search for a gene across a project
        Args:
       		1. Gene name (Required)- the name of the gene to search for
       		2. A list of project name to search for (Optional- if not given will search in all projects (Warn: Computationally Expensive!))

      '''
      self.search_for_gene(options['gene_id'], args[0])
      
      
    def search_for_gene(self,search_gene_id, project_id,proj_list=None):
      '''
        Search for a gene across project(s)
        Args:
          1. search_gene_id: Gene ID to search for
          2. proj_list: An optional list of projects to narrow down search to
        Returns:
        
        Raises:
          
      '''
      project = Project.objects.filter(project_id=project_id)[0]
      gene_id = get_gene_id_from_str(search_gene_id, get_reference())
      gene = get_reference().get_gene(gene_id)
      
      sys.stderr.write(project_id + " - staring gene search for: %s %s \n" % (search_gene_id, gene))

      # all rare coding variants
      variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)

      rare_variants = []
      for variant in project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter):
        max_af = max(variant.annotation['freqs'].values())
        if max_af < .01:
            rare_variants.append(variant)
  
      add_extra_info_to_variants_project(get_reference(), project, rare_variants)

      # compute knockout individuals
      individ_ids_and_variants = []
      knockout_ids, variation = get_knockouts_in_gene(project, gene_id)
      for indiv_id in knockout_ids:
          variants = variation.get_relevant_variants_for_indiv_ids([indiv_id])
          add_extra_info_to_variants_project(get_reference(), project, variants)
          individ_ids_and_variants.append({
              'indiv_id': indiv_id,
              'variants': variants,
          })
  
      sys.stderr.write("Project-wide gene search retrieved %s rare variants for gene: %s \n" % (len(rare_variants), gene_id))
      
      download_csv='rare_variants'
      if download_csv == 'rare_variants':
          #individuals_to_include = []
          #for variant in rare_variants:
              #for indiv_id, genotype in variant.genotypes.items():
                  #if genotype.num_alt > 0 and indiv_id not in individuals_to_include:
                      #individuals_to_include.append(indiv_id)
          rows = []
          for variant in rare_variants:
              worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"][gene_id]
              worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
              #genotypes = []
              all_genotypes_string = ""
              for indiv_id, genotype in variant.genotypes.items():
                  #genotype = variant.genotypes[indiv_id]
                  if genotype.num_alt > 0:
                    allele_string = ">".join(genotype.alleles)
                    all_genotypes_string += indiv_id + ":" + allele_string + "  "
                  #if genotype.num_alt > 0:
                      #genotypes.append(allele_string + "   (" + str(genotype.gq) + ")")
                  #else:
                  #    genotypes.append("")

              measureset_id, clinvar_significance = settings.CLINVAR_VARIANTS.get(variant.unique_tuple(), ("", ""))
              rows.append(map(str,
                  [project_id, 
                   gene["symbol"],
                    variant.chr,
                    variant.pos,
                    variant.ref,
                    variant.alt,
                    variant.vcf_id or "",
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
                    all_genotypes_string,
                  ]))


      header = ["project_id","gene", "chr", "pos", "ref", "alt", "rsID", "impact",
                "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
                "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
                "freq_exac_v3", "freq_exac_v3_popmax",
                "all_genotypes"]

      outfile=open('results_'+search_gene_id + '.tsv','w')
      writer = csv.writer(outfile,delimiter='\t')
      writer.writerow(header)
      for row in rows:
          writer.writerow(row)
      

      for individ_id_and_variants in individ_ids_and_variants:
          variants = individ_id_and_variants["variants"]
          individ_id_and_variants["variants"] = [v.toJSON() for v in variants]

      result = {
          'gene': gene,
          'gene_json': json.dumps(gene),
          'project': project,
          'rare_variants_json': json.dumps([v.toJSON() for v in rare_variants]),
          'individuals_json': json.dumps([i.get_json_obj() for i in project.get_individuals()]),
          'knockouts_json': json.dumps(individ_ids_and_variants),
      }
      #print result
  
      	
      	 
  
        