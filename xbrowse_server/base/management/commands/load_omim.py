from django.core.management import BaseCommand
from django.conf import settings
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator
from xbrowse_server.mall import get_mall, get_reference

from collections import defaultdict
import os
import re
import sys

        
class Command(BaseCommand):
    def handle(self, *args, **options):
        """Loads omim ids and phenotypes from 2 files downloaded from http://www.omim.org/downloads"""

        mim2gene_path = os.path.join(settings.REFERENCE_SETTINGS.xbrowse_reference_data_dir, "omim/mim2gene.txt")
        genemap_path =  os.path.join(settings.REFERENCE_SETTINGS.xbrowse_reference_data_dir, "omim/genemap2.txt")
        if not os.path.isfile(mim2gene_path):
            sys.exit("File not found: " + mim2gene_path)
        if not os.path.isfile(genemap_path):
            sys.exit("File not found: " + genemap_path)

        gene_to_mim_id = {}
        with open(mim2gene_path) as f:
            types = set()
            for line in f:
                if line.startswith("#"):
                    print("Commment: " + line)
                    continue
                fields = line.strip('\n').split('\t')
                mim_number = fields[0]
                entry_type = fields[1]
                gene_id = fields[-1]
                types.add(entry_type)
                if gene_id == "-" or entry_type != "gene":
                    print("Skipping " + str(fields))
                    continue
                #print(line.strip('\n').split('\t'))
                gene_to_mim_id[gene_id] = mim_number
                
            print("Loaded %d genes + mim ids" % len(gene_to_mim_id))
            print("Types: " + str(types))


        gene_mim_id_to_phenotypes = defaultdict(list)
        with open(genemap_path) as f:
            for line in f:
                if line.startswith("#"):
                    print("Commment: " + line)
                    continue
                fields = line.strip('\n').split('|')
                gene_mim_id = fields[8]
                phenotypes = fields[-3].split(";")
                for phenotype in phenotypes:
                    phenotype_map_match = re.search('(\d{4,}) (\([1-4]\)) *$', phenotype)
                    if phenotype_map_match:
                        phenotype_mim_id = phenotype_map_match.group(1)
                        phenotype_map_method = phenotype_map_match.group(2) # Phenotype mapping method - appears in parentheses after a disorder - eg. (3)

                        description = phenotype.replace(phenotype_mim_id, '').replace(phenotype_map_method, '').strip(" ,}{?")
                        gene_mim_id_to_phenotypes[gene_mim_id].append({'mim_id': phenotype_mim_id, 'description': description})
                    elif phenotype:
                        gene_mim_id_to_phenotypes[gene_mim_id].append({'mim_id': '', 'description': phenotype.strip(" ,}{?")})

                    #print((gene_mim_id, phenotype_mim_id, description))
                    #print(gene_mim_id, gene_mim_id_to_phenotypes[gene_mim_id])

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
            if gene_id in gene_to_mim_id:
                gene_mim_id = gene_to_mim_id[gene_id]
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
