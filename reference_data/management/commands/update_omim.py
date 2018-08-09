import json
import logging
import os
import re
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file_to

from reference_data.models import GeneInfo

logger = logging.getLogger(__name__)

GENEMAP2_URL = "http://data.omim.org/downloads/{omim_key}/genemap2.txt"

OMIM_FIELD_NAMES = [field.name for field in GeneInfo._meta.fields if field.name.startswith("mim") or field.name.startswith("omim")]
_RESET_ALL_OMIM_FEILDS = {omim_field: None for omim_field in OMIM_FIELD_NAMES}

OMIM_PHENOTYPE_MAP_METHOD_CHOICES = {
    1: 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.',
    2: 'the disorder has been placed on the map by linkage; no mutation has been found.',
    3: 'the molecular basis for the disorder is known; a mutation has been found in the gene.',
    4: 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.',
}


class Command(BaseCommand):
    help = "populate the OMIM table. It will contain 1 row per gene / phenotype pair."

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        parser.add_argument('genemap2_file_path', nargs="?", help="path of genemap2.txt file downloaded from http://data.omim.org/downloads/{omim_key}/genemap2.txt")

    def handle(self, *args, **options):

        omim_key = options['omim_key']
        genemap2_file_path = options['genemap2_file_path']

        if genemap2_file_path:
            genemap2_file = open(genemap2_file_path)
        elif omim_key:
            genemap2_file_path = os.path.basename(GENEMAP2_URL)
            download_file_to(url=GENEMAP2_URL.format(omim_key=omim_key), local_filename=genemap2_file_path)
            genemap2_file = open(genemap2_file_path)
        else:
            raise CommandError("Must provide --omim-key or genemap2.txt file path")

        logger.info("Parsing genemap2 file")
        genemap2_records = [r for r in parse_genemap2_table(tqdm(genemap2_file, unit=" lines"))]

        logger.info("Reseting omim fields {} in all {} GeneInfo records".format(", ".join(OMIM_FIELD_NAMES), GeneInfo.objects.count()))
        GeneInfo.objects.all().update(**_RESET_ALL_OMIM_FEILDS)

        logger.info("Updating {} records with OMIM values from {}".format(len(genemap2_records), genemap2_file_path))

        gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.all().only('gene_id')}
        for omim_record in tqdm(genemap2_records, unit=" records"):
            if omim_record["gene_id"] not in gene_id_to_gene_info:
                logger.warn("WARNING: OMIM gene id {} not found in GeneInfo table. Please run update_gencode --release x".format(omim_record["gene_id"]))
            else:
                gene_info = gene_id_to_gene_info.get(omim_record["gene_id"])
                gene_info.save(**omim_record)

        logger.info("Done")


"""
This script retrieves OMIM data from omim.org and parses/converts relevant fields into a tsv table. 

==================
OMIM DATA SOURCES:
==================
OMIM provides data through an API (https://omim.org/help/api) and in downloadable files (https://omim.org/downloads/)
The geneMap API endpoint provides only gene symbols and not the Ensembl gene id, while
genemap2.txt provides both, so the genemap2.txt file is currently downloaded as the data source.


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

"""

GENEMAP2_USEFUL_COLUMNS = [
    'mim_number', 'approved_symbol', 'gene_name', 'ensembl_gene_id', 'gene_symbols', 'comments', 'phenotypes'
]


class ParsingError(Exception):
    pass


def parse_genemap2_table(omim_genemap2_file_iter):
    """Parse the genemap2 table, and yield a dictionary representing each gene-phenotype pair."""

    header_fields = None
    for i, line in enumerate(omim_genemap2_file_iter):
        line = line.rstrip('\r\n')
        if line.startswith("# Chrom") and header_fields is None:
            # process header
            header_fields = [c.lower().replace(' ', '_') for c in line.split('\t')]
            missing_columns = set(GENEMAP2_USEFUL_COLUMNS) - set(header_fields)
            if missing_columns:
                raise ParsingError("Header line: {header_fields}\n is missing columns: {missing_columns}".format(**locals()))
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
        #output_record['gene_symbol'] = record['approved_symbol'].strip() or record['gene_symbols'].split(",")[0]
        output_record['omim_gene_description'] = record['gene_name']
        output_record['omim_comments'] = record['comments']

        phenotype_field = record['phenotypes'].strip()

        phenotype_list = []
        for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?", phenotype_field):
            # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"

            phenotype_info = {}
            phenotype_info["phenotype_description"] = phenotype_match.group(1)
            phenotype_info["phenotype_mim_number"] = int(phenotype_match.group(3)) if phenotype_match.group(3) else None
            phenotype_info["phenotype_map_method"] = phenotype_match.group(4)
            phenotype_info["phenotype_inheritance"] = phenotype_match.group(6) or None

            # basic checks
            if len(phenotype_info["phenotype_description"].strip()) == 0:
                raise ParsingError("Empty phenotype description in line #{}: {}".format(i, line))

            if int(phenotype_info["phenotype_map_method"]) not in OMIM_PHENOTYPE_MAP_METHOD_CHOICES:
                raise ParsingError("Unexpected value (%s) for phenotype_map_method on line #%s: %s" % (
                    phenotype_info["phenotype_map_method"], i, phenotype_field))

            phenotype_list.append(phenotype_info)

        if len(phenotype_field) > 0 and not phenotype_list:
            raise ParsingError("Couldn't parse phenotype field {} in line #{}: {}".format(phenotype_field, line))

        output_record['omim_phenotypes'] = json.dumps(phenotype_list)

        yield output_record


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
