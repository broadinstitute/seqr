"""
This script retrieves OMIM data from omim.org and parses/converts relevant fields into a tsv table. 

==================
OMIM DATA SOURCES:
==================
OMIM provides data through an API (https://omim.org/help/api) + as downloadable files (https://omim.org/downloads/)

API endpoints: 
-------------
http://api.omim.org/api/geneMap?chromosome=1 - which returns a list of 'geneMap' objects - each representing a mimNumber, geneSymbols, geneName, comments, geneInheritance, and a phenotypeMapList which contains one or more mimNumber, phenotypeMimNumber, phenotype description, and phenotypeInheritance

http://api.omim.org/api/entry?mimNumber=612367&format=json&include=all - which returns detailed info on a particular mim id 

Files: 
-----
mim2gene.txt - contains basic info on mim numbers and their relationships. 

For example:
     100500  moved/removed
     100600  phenotype
     100640  gene    216     ALDH1A1 ENSG00000165092,ENST00000297785
     100650  gene/phenotype  217     ALDH2   ENSG00000111275,ENST00000261733

genemap2.txt - contains chrom, gene_start, gene_end, cyto_location, mim_number, gene_symbols, gene_name, approved_symbol, entrez_gene_id, ensembl_gene_id, comments, phenotypes, mouse_gene_id  -  where phenotypes contains 1 or more phenotypes in the form  { description }, phenotype_mim_number (phenotype_mapping_key), inheritance_mode; 

For example:

   # Chromosome    Genomic Position Start    Genomic Position End    Cyto Location    Computed Cyto Location    Mim Number    Gene Symbols    Gene Name    Approved Symbol    Entrez Gene ID    Ensembl Gene ID    Comments    Phenotypes    Mouse Gene Symbol/ID
   chr1    2019328    2030752    1p36.33        137163    GABRD, GEFSP5, EIG10, EJM7    Gamma-aminobutyric acid (GABA) A receptor, delta    GABRD    2563    ENSG00000187730        {Epilepsy, generalized, with febrile seizures plus, type 5, susceptibility to}, 613060 (3), Autosomal dominant; {Epilepsy, idiopathic generalized, 10}, 613060 (3), Autosomal dominant; {Epilepsy, juvenile myoclonic, susceptibility to}, 613060 (3), Autosomal dominant    Gabrd (MGI:95622)

==================
MAKING A TSV TABLE
==================

The geneMap API endpoint provides only gene symbols and not the Ensembl gene id, while genemap2.txt provides both, so the genemap2.txt file is currently downloaded as the data source.

The table contains 1 row per gene / phenotype pair.
"""

import argparse
from collections import defaultdict
import os
import re
import urllib


def make_omim_table(output_dir, output_filename="omim.tsv", omim_key=None, save_genemap2_file=True):
    """Downloads the latest 'genemap2.txt' file from http://data.omim.org/downloads/, parses it, and writes out a tab-delimitted table with 
    the following columns: 
    
    mim_number, approved_symbol, gene_name, ensembl_gene_id, gene_symbols, comments, inheritance, phenotype_mim_number,  phenotype_description, phenotype_map_method

    output_dir: output directory path
    output_filename: output filename
    omim_key: string omim key needed to access http://data.omim.org/downloads/<omim_key>/genemap2.txt
    save_genemap2_file: whether to save a copy of the raw data retrieved from omim.org into a 'genemap2.txt' file in the output_dir
    """
    columns_of_interest = ['mim_number', 'approved_symbol', 'gene_name', 'ensembl_gene_id', 'gene_symbols', 'comments', 'phenotypes']

    output_file_header = [c for c in columns_of_interest if c != 'phenotypes']  # exclude unparsed Phenotypes column 
    output_file_header += ['inheritance', 'phenotype_mim_number', 'phenotype_description', 'phenotype_map_method'] # add columns for parsed phenotype values

    outf = open(os.path.join(output_dir, output_filename), "w")
    outf.write('\t'.join(output_file_header) + '\n')

    header_fields = None
    counter = defaultdict(int)
    if save_genemap2_file:
        genemap2_file = open(os.path.join(output_dir, "genemap2.txt"), "w")
    url = "http://data.omim.org/downloads/%(omim_key)s/genemap2.txt" % locals()
    print("Parsing " + url)
    for line in urllib.urlopen(url):
        if save_genemap2_file:
            genemap2_file.write(line)

        line = line.strip('\n')
        if not line or line.startswith("#"):
            # check header is as expeted
            if line.startswith("# Chrom") and header_fields is None:
                header_fields = line.split('\t')
                header_fields = [c.lower().replace(' ', '_') for c in header_fields]

                # check for any missing columns
                missing_columns = [c for c in columns_of_interest if c not in header_fields]
                if missing_columns:
                    raise Exception("header line: %(header_fields)s\nis missing columns: %(missing_columns)s" % locals())

            continue 

        counter["input lines"] += 1

        row_fields = line.strip('\n').split('\t')
        assert len(row_fields) == len(header_fields), "unexpected number of fields: %s" % str(row_fields)

        row_dict = dict(zip(header_fields, row_fields))
        phenotypes = row_dict['phenotypes'].strip()

        d = None
        for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?", phenotypes):
            # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"
            d = {}
            d["phenotype_description"] = phenotype_match.group(1)
            d["phenotype_mim_number"] = phenotype_match.group(3) or ""
            d["phenotype_map_method"] = phenotype_match.group(4)
            d["inheritance"] = phenotype_match.group(6) or ""

            # basic checks
            assert len(d["phenotype_description"].strip()) > 0, "unexpected empty phenotype description: %(line)s" % locals()
            assert int(d["phenotype_map_method"]) > 0 and int(d["phenotype_map_method"]) <= 4, "unexpected value (%s) for phenotype_map_method in phenotypes: %s" % (
                d["phenotype_map_method"], phenotypes)

            d.update(row_dict)
            outf.write('\t'.join(d[k] for k in output_file_header) + '\n')
            counter["output lines"] += 1
            counter["output lines with ENSG id"] += 1 if row_dict['ensembl_gene_id'] else 0

        if len(phenotypes) > 0:
            counter["input lines with phenotype(s)"] += 1
            counter["input lines with phenotype(s) and ENSG id"] += 1 if row_dict['ensembl_gene_id'] else 0
            if d is None:
                raise Exception("0 phenotypes parsed from: %s" % str(phenotypes))

    print("Finished processing:")
    for k in ['input lines', 'input lines with phenotype(s)', 'input lines with phenotype(s) and ENSG id', 'output lines', 'output lines with ENSG id']:
        print("  %10s %s" % (counter[k], k))

if __name__ == "__main__":
    try:
        import configargparse
        p = configargparse.ArgumentParser(args_for_setting_config_path=["-c", "--config-file"])
    except ImportError:
        p = argparse.ArgumentParser()

    p.add_argument('-d', '--output-dir', default='.', help='output directory')
    p.add_argument('-o', '--output-filename', default='omim.tsv', help='output filename')
    p.add_argument('-k', '--omim-key', required=True)
    p.add_argument('-g', '--save-genemap2-file', action='store_true', help='whether to save a copy of the raw data '
                   'retrieved from omim.org in a \'genemap2.txt\' file in the output_dir')
    args = p.parse_args()

    make_omim_table(args.output_dir, 
                    args.output_filename, 
                    omim_key=args.omim_key, 
                    save_genemap2_file=args.save_genemap2_file)



"""
At the bottom of genemap2.txt there is:

# Phenotype Mapping Method - Appears in parentheses after a disorder :
# --------------------------------------------------------------------
# 1 - the disorder is placed on the map based on its association with
# a gene, but the underlying defect is not known.
# 2 - the disorder has been placed on the map by linkage; no mutation has
# been found.
# 3 - the molecular basis for the disorder is known; a mutation has been
# found in the gene.
# 4 - a contiguous gene deletion or duplication syndrome, multiple genes
# are deleted or duplicated causing the phenotype.
"""
