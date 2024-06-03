"""
This script retrieves OMIM data from omim.org and parses/converts relevant fields into a tsv table.

==================
OMIM DATA SOURCES:
==================
OMIM provides data through an API (https://omim.org/help/api) and in downloadable files (https://omim.org/downloads/)
The geneMap API endpoint provides only gene symbols and not the Ensembl gene id, while
genemap2.txt provides both, so we use genemap2.txt as the data source.

Files:
-----
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

from django.core.management.base import CommandError

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import Omim

logger = logging.getLogger(__name__)


CACHED_RECORDS_BUCKET = 'seqr-reference-data/omim/'
CACHED_RECORDS_FILENAME = 'parsed_omim_records.txt'
CACHED_RECORDS_HEADER = [
    'gene_id', 'mim_number', 'gene_description', 'comments', 'phenotype_description',
    'phenotype_mim_number', 'phenotype_map_method', 'phenotype_inheritance',
    'chrom', 'start', 'end',
]

class CachedOmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim
    url = 'https://storage.googleapis.com/{bucket}{filename}'.format(
        filename=CACHED_RECORDS_FILENAME, bucket=CACHED_RECORDS_BUCKET)
    allow_missing_gene = True

    @staticmethod
    def get_file_header(f):
        return CACHED_RECORDS_HEADER

    @staticmethod
    def parse_record(record):
        yield {k: v or None for k, v in record.items()}


class OmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim
    url = "https://data.omim.org/downloads/{omim_key}/genemap2.txt"
    allow_missing_gene = True

    def __init__(self, omim_key=None, skip_cache_parsed_records=False, **kwargs):
        """Init OMIM handler."""
        if not omim_key:
            raise CommandError("omim_key is required")

        self.url = self.url.format(omim_key=omim_key)
        self.omim_key = omim_key
        self.cache_parsed_records = not skip_cache_parsed_records
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
            elif 'account is inactive' in line or 'account has expired' in line:
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
            output_record = {
                'gene_id': record['ensembl_gene_id'],
                'mim_number': int(record['mim_number']),
                'chrom': record['#_chromosome'].replace('chr', ''),
                'start': int(record['genomic_position_start']),
                'end': int(record['genomic_position_end']),
                'gene_symbol': record['approved_gene_symbol'].strip() or record['gene/locus_and_other_related_symbols'].split(",")[0],
                'gene_description': record['gene_name'],
                'comments': record['comments'],
            }

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

                yield record_with_phenotype

            if record_with_phenotype is None:
                if len(phenotype_field) > 0:
                    raise ValueError("No phenotypes found: {}".format(json.dumps(record)))
                else:
                    yield output_record

    def post_process_models(self, models):
        if self.cache_parsed_records:
            self._cache_records(models)

    @staticmethod
    def _cache_records(models):
        with open(CACHED_RECORDS_FILENAME, 'w') as f:
            f.write('\n'.join([
                '\t'.join([model.gene.gene_id if model.gene else ''] + [str(getattr(model, field) or '') for field in CACHED_RECORDS_HEADER[1:]])
                for model in models]))

        command = 'gsutil mv {filename} gs://{bucket}'.format(filename=CACHED_RECORDS_FILENAME, bucket=CACHED_RECORDS_BUCKET)
        logger.info(command)
        os.system(command)  # nosec


class Command(GeneCommand):
    reference_data_handler = OmimReferenceDataHandler

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        parser.add_argument('--skip-cache-parsed-records', action='store_true', help='write the parsed records to google storage for reuse')
        super(Command, self).add_arguments(parser)
