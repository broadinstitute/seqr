
"""
This script retrieves OMIM data from omim.org and parses/converts relevant fields into a tsv table.

==================
OMIM DATA SOURCES:
==================
OMIM provides data through an API (https://omim.org/help/api) and in downloadable files (https://omim.org/downloads/)
The geneMap API endpoint provides only gene symbols and not the Ensembl gene id, while
genemap2.txt provides both, so we use genemap2.txt as the data source.


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

Example genemap2.txt record:

   # Chromosome    Genomic Position Start    Genomic Position End    Cyto Location    Computed Cyto Location    Mim Number    Gene Symbols    Gene Name    Approved Symbol    Entrez Gene ID    Ensembl Gene ID    Comments    Phenotypes    Mouse Gene Symbol/ID
   chr1    2019328    2030752    1p36.33        137163    GABRD, GEFSP5, EIG10, EJM7    Gamma-aminobutyric acid (GABA) A receptor, delta    GABRD    2563    ENSG00000187730        {Epilepsy, generalized, with febrile seizures plus, type 5, susceptibility to}, 613060 (3), Autosomal dominant; {Epilepsy, idiopathic generalized, 10}, 613060 (3), Autosomal dominant; {Epilepsy, juvenile myoclonic, susceptibility to}, 613060 (3), Autosomal dominant    Gabrd (MGI:95622)

"""

import collections
import logging
import os
import re
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file

from reference_data.models import GeneInfo, OMIM

logger = logging.getLogger(__name__)

GENEMAP2_URL = "http://data.omim.org/downloads/{omim_key}/genemap2.txt"

OMIM_PHENOTYPE_MAP_METHOD_CHOICES = {
    1: 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.',
    2: 'the disorder has been placed on the map by linkage; no mutation has been found.',
    3: 'the molecular basis for the disorder is known; a mutation has been found in the gene.',
    4: 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.',
}


class Command(BaseCommand):
    help = "Downloads the latest OMIM genemap2.txt data and populates the OMIM table so it contains 1 row per gene-phenotype pair"

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        parser.add_argument(
            'genemap2_file_path',
            nargs="?",
            help="path of genemap2.txt file downloaded from http://data.omim.org/downloads/{omim_key}/genemap2.txt")

    def handle(self, *args, **options):
        if GeneInfo.objects.count() == 0:
            raise CommandError("GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")
        update_omim(omim_key=options['omim_key'], genemap2_file_path=options['genemap2_file_path'])


def update_omim(omim_key=None, genemap2_file_path=None):
    """Updates the OMIM table, using either the genemap2_file_path to load an existing local genemap2.txt file, or
    if an omim_key is provided instead, using the omim_key to download the file from https://www.omim.org

    Args:
        omim_key (str): OMIM download key obtained by filling in a form at https://www.omim.org/downloads/
        genemap2_file_path (str):
    """
    if genemap2_file_path:
        genemap2_file = open(genemap2_file_path)
    elif omim_key:
        genemap2_file_path = download_file(url=GENEMAP2_URL.format(omim_key=omim_key))
        genemap2_file = open(genemap2_file_path)
    else:
        raise CommandError("Must provide --omim-key or genemap2.txt file path")

    logger.info("Parsing genemap2 file")
    genemap2_records = [r for r in parse_genemap2_table(tqdm(genemap2_file, unit=" lines"))]

    logger.info("Deleting {} existing OMIM records".format(OMIM.objects.count()))
    OMIM.objects.all().delete()

    logger.info("Creating {} OMIM gene-phenotype association records".format(len(genemap2_records)))
    gene_symbol_to_gene_id = collections.defaultdict(set)  # lookup for symbols that have a 1-to-1 mapping to ENSG ids in gencode
    gene_id_to_gene_info = {}
    for gene_info in GeneInfo.objects.all().only('gene_id', 'gene_symbol'):
        gene_symbol_to_gene_id[gene_info.gene_symbol].add(gene_info.gene_id)
        gene_id_to_gene_info[gene_info.gene_id] = gene_info

    skip_counter = 0
    for omim_record in tqdm(genemap2_records, unit=" records"):
        gene_id = omim_record["gene_id"]
        gene_symbol = omim_record["gene_symbol"]
        if not gene_id and len(gene_symbol_to_gene_id.get(gene_symbol, [])) == 1:
            gene_id = iter(gene_symbol_to_gene_id[gene_symbol]).next()
            omim_record["gene_id"] = gene_id
            logger.info("Mapped gene symbol {} to gene_id {}".format(gene_symbol, gene_id))

        gene = gene_id_to_gene_info.get(gene_id)
        if not gene:
            skip_counter += 1
            logger.warn(("OMIM gene id '{}' not found in GeneInfo table. "
                         "Running ./manage.py update_gencode to update the gencode version might fix this. "
                         "Full OMIM record: {}").format(gene_id, omim_record))
            continue

        del omim_record["gene_id"]
        del omim_record["gene_symbol"]

        omim_record['gene'] = gene
        OMIM.objects.create(**omim_record)

    logger.info("Done")
    logger.info("Loaded {} OMIM records from {}. Skipped {} records with unrecognized gene id".format(
        OMIM.objects.count(), genemap2_file_path, skip_counter))


class ParsingError(Exception):
    pass


def parse_genemap2_table(omim_genemap2_file_iter):
    """Parse the genemap2 table, and yield a dictionary representing each gene-phenotype pair."""

    header_fields = None
    for i, line in enumerate(omim_genemap2_file_iter):
        line = line.rstrip('\r\n')
        if line.startswith("# Chrom") and header_fields is None:
            header_fields = [c.lower().replace(' ', '_') for c in line.split('\t')]
            continue
        elif not line or line.startswith("#"):
            continue
        elif line.startswith('This account is inactive'):
            raise Exception(line)
        elif header_fields is None:
            raise ValueError("Header row not found in genemap2 file before line {}: {}".foramt(i, line))

        fields = line.rstrip('\r\n').split('\t')
        if len(fields) != len(header_fields):
            raise ParsingError("Found %s instead of %s fields in line #%s: %s" % (
                len(fields), len(header_fields), i, str(fields)))

        record = dict(zip(header_fields, fields))

        # rename some of the fields
        output_record = {}
        output_record['gene_id'] = record['ensembl_gene_id']
        output_record['mim_number'] = int(record['mim_number'])
        output_record['gene_symbol'] = record['approved_symbol'].strip() or record['gene_symbols'].split(",")[0]
        output_record['gene_description'] = record['gene_name']
        output_record['comments'] = record['comments']

        phenotype_field = record['phenotypes'].strip()

        record_with_phenotype = None
        for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?", phenotype_field):
            # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"

            record_with_phenotype = dict(output_record) # copy
            record_with_phenotype["phenotype_description"] = phenotype_match.group(1)
            record_with_phenotype["phenotype_mim_number"] = int(phenotype_match.group(3)) if phenotype_match.group(3) else None
            record_with_phenotype["phenotype_map_method"] = phenotype_match.group(4)
            record_with_phenotype["phenotype_inheritance"] = phenotype_match.group(6) or None

            # basic checks
            if len(record_with_phenotype["phenotype_description"].strip()) == 0:
                raise ParsingError("Empty phenotype description in line #{}: {}".format(i, line))

            if int(record_with_phenotype["phenotype_map_method"]) not in OMIM_PHENOTYPE_MAP_METHOD_CHOICES:
                raise ParsingError("Unexpected value (%s) for phenotype_map_method on line #%s: %s" % (
                    record_with_phenotype["phenotype_map_method"], i, phenotype_field))

            yield record_with_phenotype

        if len(phenotype_field) > 0 and record_with_phenotype is None:
            raise ParsingError("No phenotypes found in line #{}: {}".format(i, line))

"""
Comment at the end of genemap2.txt:

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
