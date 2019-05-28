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

import json
import logging
import os
import re
import requests

from django.core.management.base import CommandError

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import Omim

logger = logging.getLogger(__name__)

OMIM_ENTRIES_URL = 'https://api.omim.org/api/entry?apiKey={omim_key}&include=geneMap&format=json&mimNumber={mim_numbers}'

OMIM_PHENOTYPE_MAP_METHOD_CHOICES = {
    1: 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.',
    2: 'the disorder has been placed on the map by linkage; no mutation has been found.',
    3: 'the molecular basis for the disorder is known; a mutation has been found in the gene.',
    4: 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.',
}


class OmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim
    url = "http://data.omim.org/downloads/{omim_key}/genemap2.txt"

    def __init__(self, omim_key=None, **kwargs):
        if not omim_key:
            raise CommandError("omim_key is required")

        self.url = self.url.format(omim_key=omim_key)
        self.omim_key = omim_key
        super(OmimReferenceDataHandler, self).__init__()

    @staticmethod
    def get_file_header(f):
        header_fields = None
        for i, line in enumerate(f):
            line = line.rstrip('\r\n')
            if line.startswith("# Chrom") and header_fields is None:
                header_fields = [c.lower().replace(' ', '_') for c in line.split('\t')]
                break
            elif not line or line.startswith("#"):
                continue
            elif line.startswith('This account is inactive') or line.startswith('This account has expired'):
                raise Exception(line)
            elif header_fields is None:
                raise ValueError("Header row not found in genemap2 file before line {}: {}".format(i, line))

        return header_fields

    @staticmethod
    def parse_record(record):
        # skip commented rows
        if len(record) == 1:
            yield None

        else:
            # rename some of the fields
            output_record = {}
            output_record['gene_id'] = record['ensembl_gene_id']
            output_record['mim_number'] = int(record['mim_number'])
            output_record['gene_symbol'] = record['approved_symbol'].strip() or record['gene_symbols'].split(",")[0]
            output_record['gene_description'] = record['gene_name']
            output_record['comments'] = record['comments']

            phenotype_field = record['phenotypes'].strip()

            record_with_phenotype = None
            for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?",
                                               phenotype_field):
                # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"

                record_with_phenotype = dict(output_record)  # copy
                record_with_phenotype["phenotype_description"] = phenotype_match.group(1)
                record_with_phenotype["phenotype_mim_number"] = int(phenotype_match.group(3)) if phenotype_match.group(
                    3) else None
                record_with_phenotype["phenotype_map_method"] = phenotype_match.group(4)
                record_with_phenotype["phenotype_inheritance"] = phenotype_match.group(6) or None

                # basic checks
                if len(record_with_phenotype["phenotype_description"].strip()) == 0:
                    raise ValueError("Empty phenotype description: {}".format(json.dumps(record)))

                if int(record_with_phenotype["phenotype_map_method"]) not in OMIM_PHENOTYPE_MAP_METHOD_CHOICES:
                    raise ValueError("Unexpected value (%s) for phenotype_map_method: %s" % (
                        record_with_phenotype["phenotype_map_method"], phenotype_field))

                yield record_with_phenotype

            if record_with_phenotype is None:
                if len(phenotype_field) > 0:
                    raise ValueError("No phenotypes found: {}".format(json.dumps(record)))
                else:
                    yield output_record

    def post_process_models(self, models):
        logger.info('Adding phenotypic series information')
        mim_numbers = {omim_record.mim_number for omim_record in models if omim_record.phenotype_mim_number}
        mim_numbers = map(str, list(mim_numbers))
        mim_number_to_phenotypic_series = {}
        for i in range(0, len(mim_numbers), 20):
            logger.debug('Fetching entries {}-{}'.format(i, i + 20))
            entries_to_fetch = mim_numbers[i:i + 20]
            response = requests.get(OMIM_ENTRIES_URL.format(omim_key=self.omim_key, mim_numbers=','.join(entries_to_fetch)))
            if not response.ok:
                raise CommandError('Request failed with {}: {}'.format(response.status_code, response.reason))

            entries = response.json()['omim']['entryList']
            if len(entries) != len(entries_to_fetch):
                raise CommandError(
                    'Expected {} omim entries but recieved {}'.format(len(entries_to_fetch), len(entries)))

            for entry in entries:
                mim_number = entry['entry']['mimNumber']
                for phenotype in entry['entry'].get('geneMap', {}).get('phenotypeMapList', []):
                    phenotypic_series_number = phenotype['phenotypeMap'].get('phenotypicSeriesNumber')
                    if phenotypic_series_number:
                        mim_number_to_phenotypic_series[mim_number] = phenotypic_series_number

        for omim_record in models:
            omim_record.phenotypic_series_number = mim_number_to_phenotypic_series.get(omim_record.mim_number)
        logger.info('Found {} records with phenotypic series'.format(len(mim_number_to_phenotypic_series)))


class Command(GeneCommand):
    reference_data_handler = OmimReferenceDataHandler

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        super(Command, self).add_arguments(parser)
