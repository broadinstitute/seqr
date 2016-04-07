from django.core.management import BaseCommand
from django.conf import settings
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator
from xbrowse_server.mall import get_mall, get_reference

from collections import defaultdict
import os
import re
import sys

        
class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')


    def handle(self, *args, **options):
        """Loads omim ids and phenotypes from 2 files downloaded from http://www.omim.org/downloads"""

        genemap_path =  os.path.join(settings.REFERENCE_SETTINGS.xbrowse_reference_data_dir, "omim/genemap2.txt")
        if not os.path.isfile(genemap_path):
            sys.exit("File not found: " + genemap_path)

        gene_id_to_mim_id = {}
        gene_mim_id_to_phenotypes = defaultdict(list)
        with open(genemap_path) as f:
            for line in f:
                if not line or line.startswith("#"):
                    #print("Comment: " + line.strip('\n'))
                    continue
                fields = line.strip('\n').split('\t')
                try:
                    gene_mim_id = fields[5]
                    if gene_mim_id:
                        int(gene_mim_id)
                    gene_id = fields[10]
                    phenotypes = fields[12].split(";")
                except Exception as e:
                    print("Exception: %s while parsing line: %s" % (e, fields)) 
                    continue

                if not gene_mim_id or not gene_id:
                    continue
                assert gene_id.startswith("ENSG"), "Unexpected gene id: %s" % gene_id

                gene_id_to_mim_id[gene_id] = gene_mim_id
                for phenotype in phenotypes:
                    phenotype_map_match = re.search('(\d{4,}) (\([1-4]\)) *$', phenotype)
                    if phenotype_map_match:
                        phenotype_mim_id = phenotype_map_match.group(1)
                        phenotype_map_method = phenotype_map_match.group(2) # Phenotype mapping method - appears in parentheses after a disorder - eg. (3)

                        description = phenotype.replace(phenotype_mim_id, '').replace(phenotype_map_method, '').strip(" ,}{?")
                        gene_mim_id_to_phenotypes[gene_mim_id].append({'mim_id': phenotype_mim_id, 'description': description})
                    elif phenotype:
                        gene_mim_id_to_phenotypes[gene_mim_id].append({'mim_id': '', 'description': phenotype.strip(" ,}{?")})
                        
                    print("gene_mim_id: %s = %s = %s" % (gene_mim_id, gene_id, gene_mim_id_to_phenotypes[gene_mim_id])) 
        print("Loaded %s genes, %s mim ids, and %s phenotypes" % ( len(gene_id_to_mim_id), len(gene_mim_id_to_phenotypes), sum(len(v) for k, v in gene_mim_id_to_phenotypes.items())))


        """
          example phenotype_info: for RYR1 it would be:
          {
             'has_mendelian_phenotype': true,
             'mim_id': "180901",  # gene id
             'mim_phenotypes': [
                {'mim_id': '117000', 'description': 'CENTRAL CORE DISEASE OF MUSCLE'},
                ...
             ],
             'orphanet_phenotypes': [
                {'orphanet_id': '178145', 'description': 'Moderate multiminicore disease with hand involvement'},
                ...
             ]
           }
        """
        for gene_id in get_reference().get_all_gene_ids(): 
            gene_mim_id = None
            if gene_id in gene_id_to_mim_id:
                gene_mim_id = gene_id_to_mim_id[gene_id]
            if gene_mim_id:
                phenotypes = { 
                    'has_mendelian_phenotype': True,
                    'mim_id': gene_mim_id,
                    'mim_phenotypes': gene_mim_id_to_phenotypes[gene_mim_id],
                    'orphanet_phenotypes' : [],
                }
                print("Updated %(gene_id)s to %(phenotypes)s" % locals())
                get_reference().update_phenotype_info(gene_id, phenotypes)


"""
Phenotype map methods:

1 - the disorder is placed on the map based on its association with
a gene, but the underlying defect is not known.
2 - the disorder has been placed on the map by linkage; no mutation has
been found.
3 - the molecular basis for the disorder is known; a mutation has been
found in the gene.
4 - a contiguous gene deletion or duplication syndrome, multiple genes
are deleted or duplicated causing the phenotype.
"""
