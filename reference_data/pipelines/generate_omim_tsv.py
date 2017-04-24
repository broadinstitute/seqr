"""
This script retrieves OMIM data from omim.org and parses/converts relevant fields into a tsv table. 

==================
OMIM DATA SOURCES:
==================
OMIM provides data through an API (https://omim.org/help/api) and in
downloadable files (https://omim.org/downloads/)

API endpoints: 
-------------
http://api.omim.org/api/geneMap?chromosome=1
   returns a list of 'geneMap' objects - each representing a
   mimNumber, geneSymbols, geneName, comments, geneInheritance, and a phenotypeMapList
   which contains one or more mimNumber, phenotypeMimNumber, phenotype description, and
   phenotypeInheritance

http://api.omim.org/api/entry?mimNumber=612367&format=json&include=all
   returns detailed info on a particular mim id

Files: 
-----
mim2gene.txt - contains basic info on mim numbers and their relationships. 

For example:
     100500  moved/removed
     100600  phenotype
     100640  gene    216     ALDH1A1 ENSG00000165092,ENST00000297785
     100650  gene/phenotype  217     ALDH2   ENSG00000111275,ENST00000261733

genemap2.txt - contains chrom, gene_start, gene_end, cyto_location, mim_number,
    gene_symbols, gene_name, approved_symbol, entrez_gene_id, ensembl_gene_id, comments, phenotypes,
    mouse_gene_id  -  where phenotypes contains 1 or more phenotypes in the form
    { description }, phenotype_mim_number (phenotype_mapping_key), inheritance_mode;

For example:

   # Chromosome    Genomic Position Start    Genomic Position End    Cyto Location    Computed Cyto Location    Mim Number    Gene Symbols    Gene Name    Approved Symbol    Entrez Gene ID    Ensembl Gene ID    Comments    Phenotypes    Mouse Gene Symbol/ID
   chr1    2019328    2030752    1p36.33        137163    GABRD, GEFSP5, EIG10, EJM7    Gamma-aminobutyric acid (GABA) A receptor, delta    GABRD    2563    ENSG00000187730        {Epilepsy, generalized, with febrile seizures plus, type 5, susceptibility to}, 613060 (3), Autosomal dominant; {Epilepsy, idiopathic generalized, 10}, 613060 (3), Autosomal dominant; {Epilepsy, juvenile myoclonic, susceptibility to}, 613060 (3), Autosomal dominant    Gabrd (MGI:95622)

==================
MAKING A TSV TABLE
==================

The geneMap API endpoint provides only gene symbols and not the Ensembl gene id, while
genemap2.txt provides both, so the genemap2.txt file is currently downloaded as the data source.

The table contains 1 row per gene / phenotype pair.
"""

import argparse
from collections import defaultdict
import os
import re
import urllib


GENEMAP2_USEFUL_COLUMNS = [
    'mim_number', 'approved_symbol', 'gene_name', 'ensembl_gene_id', 'gene_symbols', 'comments', 'phenotypes'
]

OUTPUT_COLUMNS = [
    'mim_number',       #  601365
    'gene_id',          # "ENSG00000107404"
    'gene_symbol',      # "DVL1"
    'gene_description', # "Dishevelled 1 (homologous to Drosophila dsh)"
    'comments',         # "associated with rs10492972"

    'phenotype_inheritance',   # "Autosomal dominant"
    'phenotype_mim_number',    #  616331
    'phenotype_description',   # "Robinow syndrome, autosomal dominant 2"
    'phenotype_map_method'     # 2
]


class ParsingError(Exception):
    pass

def parse_genemap2_table(omim_genemap2_file_iterator):
    """Parse the genemap2 table, and yield a dictionary representing each gene-phenotype pair."""

    header_fields = None
    for i, line in enumerate(omim_genemap2_file_iterator):
        line = line.rstrip('\n')
        if not line or line.startswith("#"):
            # make sure file header contains the expected columns
            if line.startswith("# Chrom") and header_fields is None:
                header_fields = line.split('\t')
                header_fields = [c.lower().replace(' ', '_') for c in header_fields]

                # check for any missing columns
                missing_columns = [c for c in GENEMAP2_USEFUL_COLUMNS if c not in header_fields]
                if missing_columns:
                    raise ParsingError("Header line: %(header_fields)s\n"
                        "is missing columns: %(missing_columns)s" % locals())

            continue

        if line.startswith('This account is inactive'):
            raise Exception(line)
        
        if header_fields is None:
            raise ValueError("Header row not found. Is the OMIM data source valid?")

        fields = line.strip('\n').split('\t')
        if len(fields) != len(header_fields):
            raise ParsingError("Found %s instead of %s fields in line #%s: %s" % (
                len(fields), len(header_fields), i, str(fields)))

        record = dict(zip(header_fields, fields))

        # rename some of the fields
        record['gene_id'] = record['ensembl_gene_id']
        record['gene_symbol'] = record['approved_symbol'].strip() or record['gene_symbols'].split(",")[0]
        record['gene_description'] = record['gene_name']

        phenotypes = record['phenotypes'].strip()

        record = {k: v for k, v in record.items() if k in set(OUTPUT_COLUMNS)}

        record_with_phenotype = None
        for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?", phenotypes):
            # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"

            record_with_phenotype = dict(record) # copy
            record_with_phenotype["phenotype_description"] = phenotype_match.group(1)
            record_with_phenotype["phenotype_mim_number"] = phenotype_match.group(3) or None
            record_with_phenotype["phenotype_map_method"] = phenotype_match.group(4)
            record_with_phenotype["phenotype_inheritance"] = phenotype_match.group(6) or None

            # basic checks
            if len(record_with_phenotype["phenotype_description"].strip()) == 0:
                raise ParsingError("Empty phenotype description in line #%s: %s" % (i, phenotypes))

            if int(record_with_phenotype["phenotype_map_method"]) not in (1, 2, 3, 4):
                raise ParsingError("Unexpected value (%s) for phenotype_map_method on line #%s: %s" % (
                    record_with_phenotype["phenotype_map_method"], i, phenotypes))

            yield record_with_phenotype

        if len(phenotypes) > 0 and record_with_phenotype is None:
            raise ParsingError("0 phenotypes parsed from line #%s: %s" % (i, str(phenotypes)))


def generate_omim_table(output_dir, output_filename="omim.tsv", omim_key=None, save_genemap2_file=False):
    """Downloads the latest 'genemap2.txt' file from http://data.omim.org/downloads/, parses it,
    and writes out a tab-delimitted table with the following columns:

    mim_number, approved_symbol, gene_name, ensembl_gene_id, gene_symbols, comments, inheritance,
    phenotype_mim_number,  phenotype_description, phenotype_map_method

    Args:
        output_dir (string): output directory path
        output_filename (string): output filename
        omim_key (string): OMIM requires (free) registration and provides a key to use when
            downloading  files (eg. http://data.omim.org/downloads/<omim_key>/genemap2.txt )
        save_genemap2_file (bool): whether to save a copy of the raw data retrieved from
            omim.org into a 'genemap2.txt' file in the output_dir
    """

    url = "http://data.omim.org/downloads/%(omim_key)s/genemap2.txt" % locals()
    print("Parsing " + url)
    if save_genemap2_file:
        genemap2_path = os.path.join(output_dir, "genemap2.txt")
        with open(genemap2_path, "w") as genemap2_file:
            for line in urllib.urlopen(url):
                genemap2_file.write(line)
        genemap2_file = open(genemap2_path)
    else:
        genemap2_file = urllib.urlopen(url)

    counter = defaultdict(int)
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, "w") as outf:
        outf.write('\t'.join(OUTPUT_COLUMNS) + '\n')

        for record in parse_genemap2_table(genemap2_file):
            outf.write('\t'.join(record[k] for k in OUTPUT_COLUMNS) + '\n')

            counter["total"] += 1
            counter["lines with ENSG id"] += 1 if record['ensembl_gene_id'] else 0

    print("Wrote %s lines to %s" % (counter['total'], output_path))
    print("    %0.2f%% of them had an ENSG id." % (100.0*counter['lines with ENSG id']/counter['total']))


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

    generate_omim_table(
        args.output_dir,
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
