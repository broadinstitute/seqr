import csv

from collections import defaultdict
from django.db import models, transaction
import gzip
import json
import logging
import re
import requests
from tqdm import tqdm

from reference_data.utils.dbnsfp_utils import DBNSFP_FIELD_MAP, DBNSFP_EXCLUDE_FIELDS
from reference_data.utils.download_utils import download_file
from reference_data.utils.gencode_utils import parse_gencode_record, GENCODE_URL_TEMPLATE, GENCODE_FILE_HEADER
from seqr.views.utils.export_utils import write_multiple_files

#  Allow adding the custom json_fields and internal_json_fields to the model Meta
# (from https://stackoverflow.com/questions/1088431/adding-attributes-into-django-models-meta-class)
models.options.DEFAULT_NAMES = models.options.DEFAULT_NAMES + ('json_fields',)

logger = logging.getLogger(__name__)

GENOME_VERSION_GRCh37 = "37"
GENOME_VERSION_GRCh38 = "38"

GENOME_VERSION_CHOICES = [
    (GENOME_VERSION_GRCh37, "GRCh37"),
    (GENOME_VERSION_GRCh38, "GRCh38")
]
GENOME_VERSION_LOOKUP = {k: v for (k, v) in GENOME_VERSION_CHOICES}


class ReferenceDataRouter(object):
    """
    A router to control all database operations on reference data models
    """
    @classmethod
    def db_for_read(cls, model, **hints):
        """
        Attempts to read reference_data models go to reference_data_db.
        """
        if model._meta.app_label == 'reference_data':
            return 'reference_data'
        return None

    @classmethod
    def db_for_write(cls, model, **hints):
        """
        Attempts to write reference_data models go to reference_data_db.
        """
        if model._meta.app_label == 'reference_data':
            return 'reference_data'
        return None

    @classmethod
    def allow_relation(cls, obj1, obj2, **hints):
        """
        Allow relations if a model in the reference_data app is involved.
        """
        if obj1._meta.app_label == 'reference_data' or \
           obj2._meta.app_label == 'reference_data':
           return True
        return None

    @classmethod
    def allow_migrate(cls, db, app_label, model_name=None, **hints):
        """
        Make sure the reference_data app only appears in the 'reference_data_db'
        database.
        """
        if app_label == 'reference_data':
            return db == 'reference_data'
        elif db == 'reference_data':
            return False
        return None


class LoadableModel(models.Model):

    CURRENT_VERSION = None
    URL = None

    class Meta:
        abstract = True

    @classmethod
    def get_url(cls, **kwargs):
        return cls.URL

    @classmethod
    def get_current_version(cls, **kwargs):
        return cls.CURRENT_VERSION

    @classmethod
    def _get_file_last_modified(cls, **kwargs):
        response = requests.head(cls.get_url(**kwargs), timeout=60)
        return response.headers['Last-Modified']

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield record

    @staticmethod
    def get_file_header(f):
        return next(f).rstrip('\n\r').split('\t')

    @classmethod
    def get_file_iterator(cls, f):
        return tqdm(f, unit=' records')

    @classmethod
    def get_record_models(cls, records, **kwargs):
        return [cls(**record) for record in records]

    @classmethod
    def load_records(cls, **kwargs):
        file_path = download_file(cls.get_url(**kwargs))

        logger.info(f'Parsing file {file_path}')
        open_file = gzip.open if file_path.endswith('.gz') else open
        open_mode = 'rt' if file_path.endswith('.gz') else 'r'
        with open_file(file_path, open_mode) as f:
            header_fields = cls.get_file_header(f)
            for line in cls.get_file_iterator(f):
                yield dict(zip(header_fields, line if isinstance(line, list) else line.rstrip('\r\n').split('\t')))

    @classmethod
    def update_records(cls, **kwargs):
        missing_mappings = {k for k, v in kwargs.items() if not v}
        if missing_mappings:
            raise ValueError(f'Related data is missing to load {cls.__name__}: {", ".join(sorted(missing_mappings))}')

        logger.info(f'Updating {cls.__name__}')

        records = []
        for record in cls.load_records(**kwargs):
            for record in cls.parse_record(record, **kwargs):
                if record is None:
                    continue
                records.append(record)

        models = cls.get_record_models(records, **kwargs)

        with transaction.atomic():
            deleted, _ = cls.objects.all().delete()
            logger.info(f'Deleted {deleted} {cls.__name__} records')
            cls.objects.bulk_create(models)
            logger.info(f'Created {len(models)} {cls.__name__} records')

        logger.info('Done')
        logger.info(f'Loaded {cls.objects.count()} {cls.__name__} records')


class HumanPhenotypeOntology(LoadableModel):

    URL = 'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp.obo'
    HEADER = ['hpo_id', 'is_category', 'parent_id', 'name', 'definition', 'comment']

    hpo_id = models.CharField(max_length=20, null=False, blank=False, unique=True, db_index=True)
    parent_id = models.CharField(max_length=20, null=True, blank=True)
    # hpo id of top-level phenotype category (eg. 'cardiovascular')
    category_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    # whether this hpo id is itself one of the top-level categories (eg. 'cardiovascular')
    is_category = models.BooleanField(default=False, db_index=True)

    name = models.TextField(null=False, blank=False)

    definition = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)


    @classmethod
    def get_current_version(cls, **kwargs):
        response = requests.head(cls.get_url(**kwargs), timeout=60)
        #  HPO redirects the "latest" URL to the URL of the latest release, so extract the release from the redirect Location
        redirect_url = response.headers['Location']
        return re.match(cls.URL.replace('latest/download', 'download/(.+)'), redirect_url).group(1)

    @staticmethod
    def get_file_header(f):
        return HumanPhenotypeOntology.HEADER

    @classmethod
    def get_file_iterator(cls, f):
        record = {}
        for line in super().get_file_iterator(f):
            line = line.rstrip('\n')
            value = ' '.join(line.split(' ')[1:])
            if line.startswith('id: '):
                # When encountering a new hpo ID, yield the previous record and start accumulating a new one
                if record:
                    yield [record.get(f) for f in cls.HEADER]
                record = {
                    'hpo_id': value,
                    'is_category': False,
                }
            elif line.startswith('is_a: '):
                is_a = value.split(' ! ')[0]
                if is_a == 'HP:0000118':
                    record['is_category'] = True
                record['parent_id'] = is_a
            elif line.startswith('name: '):
                record['name'] = value
            elif line.startswith('def: '):
                record['definition'] = value
            elif line.startswith('comment: '):
                record['comment'] = value

        yield [record.get(f) for f in cls.HEADER] if record else None

    @classmethod
    def get_record_models(cls, records, **kwargs):
        models = super().get_record_models(records, **kwargs)
        parent_id_map = {model.hpo_id: model.parent_id for model in models}
        for model in models:
            model.category_id = cls._get_category_id(parent_id_map, model.hpo_id)
        return models

    @staticmethod
    def _get_category_id(parent_id_map, hpo_id):
        if hpo_id == 'HP:0000001':
            return None

        if hpo_id not in parent_id_map:
            return None

        while hpo_id and parent_id_map.get(hpo_id) != 'HP:0000118':
            if hpo_id not in parent_id_map:
                raise ValueError('Strange id: %s' % hpo_id)
            hpo_id = parent_id_map[hpo_id]
            if hpo_id == 'HP:0000001':
                return None

        return hpo_id

class GeneInfo(LoadableModel):
    """Human gene models from https://www.gencodegenes.org/releases/
    http://www.gencodegenes.org/gencodeformat.html
    """

    ALL_GENCODE_VERSIONS = ['39', '31', '29', '28', '27', '19']
    CURRENT_VERSION = ALL_GENCODE_VERSIONS[0]

    # gencode fields
    gene_id = models.CharField(max_length=20, db_index=True, unique=True)   # without the version suffix (eg. "ENSG0000012345")
    gene_symbol = models.TextField(null=True, blank=True)

    chrom_grch37 = models.CharField(max_length=2, null=True, blank=True)
    start_grch37 = models.IntegerField(null=True, blank=True)
    end_grch37 = models.IntegerField(null=True, blank=True)
    strand_grch37 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch37 = models.IntegerField(default=0)  # number of protein-coding base-pairs in this gene (= 0 for non-coding genes)

    chrom_grch38 = models.CharField(max_length=2, null=True, blank=True)
    start_grch38 = models.IntegerField(null=True, blank=True)
    end_grch38 = models.IntegerField(null=True, blank=True)
    strand_grch38 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch38 = models.IntegerField(default=0)  # number of protein-coding base-pairs in this gene (= 0 for non-coding genes)

    # gencode-specific fields, although models could hypothetically come from refseq or other places
    gencode_gene_type = models.TextField(null=True, blank=True)
    gencode_release = models.IntegerField(null=True, blank=True)

    class Meta:
        json_fields = [
            'gene_id', 'gene_symbol', 'chrom_grch37', 'start_grch37', 'end_grch37', 'chrom_grch38', 'start_grch38',
            'end_grch38', 'gencode_gene_type', 'coding_region_size_grch37', 'coding_region_size_grch38',
        ]

    @classmethod
    def get_url(cls, gencode_release=None, genome_version=None, **kwargs):
        path = ''
        file = '.annotation.gtf.gz'
        if gencode_release > 22 and genome_version == GENOME_VERSION_GRCh37:
            path = 'GRCh37_mapping/'
            file = 'lift37.annotation.gtf.gz'
        return GENCODE_URL_TEMPLATE.format(path=path, file=file, gencode_release=gencode_release)

    @staticmethod
    def get_file_header(f):
        return GENCODE_FILE_HEADER

    @classmethod
    def get_file_iterator(cls, f):
        for line in super().get_file_iterator(f):
            if line and not line.startswith('#'):
                yield line

    @classmethod
    def update_records(cls, gencode_release=CURRENT_VERSION, existing_gene_ids=None, existing_transcript_ids=None, gene_symbol_change_dir=None, **kwargs):
        counters = defaultdict(int)
        genes = defaultdict(dict)
        transcripts = defaultdict(dict)

        genome_versions = []
        gencode_release = int(gencode_release)
        if gencode_release == 19 or gencode_release > 22:
            genome_versions.append(GENOME_VERSION_GRCh37)
        if gencode_release > 19:
            genome_versions.append(GENOME_VERSION_GRCh38)

        for genome_version in genome_versions:
            for record in cls.load_records(gencode_release=gencode_release, genome_version=genome_version, **kwargs):
                parse_gencode_record(
                    record, genes, transcripts, existing_gene_ids or [], existing_transcript_ids or [], counters,
                    genome_version, gencode_release
                )
        for k, v in counters.items():
            logger.info(f'{k}: {v}')

        if existing_gene_ids is not None:
            existing_gene_ids.update(genes.keys())
        if existing_transcript_ids is not None:
            existing_transcript_ids.update(transcripts.keys())

        if not genes:
            return transcripts

        genes_to_update = cls.objects.filter(gene_id__in=genes.keys(), gencode_release__lt=gencode_release)
        fields = set()
        symbol_changes = []
        for existing in genes_to_update:
            new_gene = genes.pop(existing.gene_id)
            if gene_symbol_change_dir and new_gene['gene_symbol'] != existing.gene_symbol:
                symbol_changes.append({
                    'gene_id': existing.gene_id,
                    'old_symbol': existing.gene_symbol,
                    'new_symbol': new_gene['gene_symbol'],
                })
            fields.update(new_gene.keys())
            for key, value in new_gene.items():
                setattr(existing, key, value)

        if genes_to_update:
            cls.objects.bulk_update(genes_to_update, fields)
            logger.info(f'Updated {len(genes_to_update)} previously loaded {cls.__name__} records')

        cls.objects.bulk_create([cls(**record) for record in genes.values()])
        logger.info(f'Created {len(genes)} {cls.__name__} records')

        if symbol_changes:
            write_multiple_files([
                (f'gene_symbol_changes__{gencode_release}', ['gene_id', 'old_symbol', 'new_symbol'], symbol_changes)
            ], gene_symbol_change_dir, user=None)

        return transcripts

class GeneMetadataModel(LoadableModel):

    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @classmethod
    def get_gene_for_record(cls, record, gene_ids_to_gene=None, gene_symbols_to_gene=None, **kwargs):
        gene_symbol = record.pop('gene_symbol', None)
        gene_id = record.pop('gene_id', None) or gene_symbols_to_gene.get(gene_symbol)

        return gene_ids_to_gene.get(gene_id)

    @classmethod
    def parse_record(cls, record, skipped_genes=None, **kwargs):
        record = cls.parse_gene_record(record)
        if record is not None:
            record['gene_id'] = cls.get_gene_for_record(record, **kwargs)
            if not record['gene_id']:
                skipped_genes[None] +=1
                record = None
        yield record

    @staticmethod
    def parse_gene_record(record):
        return record

    @classmethod
    def update_records(cls, **kwargs):
        skipped_genes = {None: 0}
        super().update_records(skipped_genes=skipped_genes, **kwargs)
        if skipped_genes[None]:
            logger.info(f'Skipped {skipped_genes[None]} records with unrecognized genes.')


class TranscriptInfo(GeneMetadataModel):

    transcript_id = models.CharField(max_length=20, db_index=True, unique=True)  # without the version suffix
    is_mane_select = models.BooleanField(default=False)

    chrom_grch37 = models.CharField(max_length=2, null=True, blank=True)
    start_grch37 = models.IntegerField(null=True, blank=True)
    end_grch37 = models.IntegerField(null=True, blank=True)
    strand_grch37 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch37 = models.IntegerField(default=0)  # number of protein-coding bases (= 0 for non-coding genes)

    chrom_grch38 = models.CharField(max_length=2, null=True, blank=True)
    start_grch38 = models.IntegerField(null=True, blank=True)
    end_grch38 = models.IntegerField(null=True, blank=True)
    strand_grch38 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch38 = models.IntegerField(default=0)  # number of protein-coding bases (= 0 for non-coding genes)

    class Meta:
        json_fields = ['transcript_id', 'is_mane_select']

    @classmethod
    def bulk_create_for_genes(cls, records, gene_id_map):
        cls.objects.bulk_create([
            cls(gene_id=gene_id_map[record.pop('gene_id')], **record)
            for record in records.values()
        ], batch_size=50000)
        logger.info(f'Created {len(records)} {cls.__name__} records')


class RefseqTranscript(LoadableModel):

    URL = GENCODE_URL_TEMPLATE.format(path='', file='.metadata.RefSeq.gz', gencode_release=GeneInfo.CURRENT_VERSION)

    transcript = models.OneToOneField(TranscriptInfo, on_delete=models.CASCADE)
    refseq_id = models.CharField(max_length=20)

    @staticmethod
    def get_file_header(f):
        return ['transcript_id', 'refseq_id', 'additional_info']

    @classmethod
    def parse_record(cls, record, transcript_id_map=None, skipped_transcripts=None, **kwargs):
        transcript_id = record['transcript_id'].split('.')[0]
        # only create a record for the first occurrence of a given transcript
        transcript = transcript_id_map.pop(transcript_id, None)
        if not transcript:
            skipped_transcripts[None] += 1
        yield {
            'transcript_id': transcript,
            'refseq_id': record['refseq_id'],
        } if transcript else None

    @classmethod
    def update_records(cls, **kwargs):
        transcript_id_map = dict(TranscriptInfo.objects.values_list('transcript_id', 'id'))
        skipped_transcripts = {None: 0}
        super().update_records(transcript_id_map=transcript_id_map, skipped_transcripts=skipped_transcripts, **kwargs)
        if skipped_transcripts[None]:
            logger.info(f'Skipped {skipped_transcripts[None]} records with unrecognized or duplicated transcripts')


# based on # ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3.1/functional_gene_constraint/fordist_cleaned_exac_r03_march16_z_pli_rec_null_data.txt
class GeneConstraint(GeneMetadataModel):

    CURRENT_VERSION = 'gnomad.v2.1.1.lof_metrics.by_gene'
    URL = f'http://storage.googleapis.com/seqr-reference-data/gene_constraint/{CURRENT_VERSION}.txt'

    mis_z = models.FloatField()
    mis_z_rank = models.IntegerField()
    pLI = models.FloatField()
    pLI_rank = models.IntegerField()
    louef = models.FloatField()
    louef_rank = models.IntegerField()

    class Meta:
        json_fields = ['mis_z', 'mis_z_rank', 'pLI', 'pLI_rank', 'louef', 'louef_rank']

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_id': record['gene_id'].split(".")[0],
            'gene_symbol': record['gene'],
            'mis_z': float(record['mis_z']) if record['mis_z'] != 'NaN' else -100,
            'pLI': float(record['pLI']) if record['pLI'] != 'NA' else 0,
            'louef': float(record['oe_lof_upper']) if record['oe_lof'] != 'NA' else 100,
        }

    @classmethod
    def get_record_models(cls, records, **kwargs):
        # add _rank fields
        for field, order in [('mis_z', -1), ('pLI', -1), ('louef', 1)]:
            for i, record in enumerate(sorted(records, key=lambda record: order * record[field])):
                record['{}_rank'.format(field)] = i
        return super().get_record_models(records, **kwargs)


class GeneCopyNumberSensitivity(GeneMetadataModel):

    CURRENT_VERSION = 'Collins_rCNV_2022'
    URL = f'https://zenodo.org/record/6347673/files/{CURRENT_VERSION}.dosage_sensitivity_scores.tsv.gz'

    pHI = models.FloatField()
    pTS = models.FloatField()

    class Meta:
        json_fields = ['pHI', 'pTS']

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_symbol': record['#gene'],
            'pHI': float(record['pHaplo']),
            'pTS': float(record['pTriplo']),
        }


class GeneShet(GeneMetadataModel):

    CURRENT_VERSION = '7939768'
    URL = f'https://zenodo.org/record/{CURRENT_VERSION}/files/s_het_estimates.genebayes.tsv'

    post_mean = models.FloatField()

    class Meta:
        json_fields = ['post_mean']

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_id': record['ensg'],
            'post_mean': float(record['post_mean']),
        }


class Omim(LoadableModel):

    OMIM_URL = 'https://data.omim.org/downloads/{omim_key}/genemap2.txt'

    CACHED_RECORDS_HEADER = [
        'ensembl_gene_id', 'mim_number', 'gene_description', 'comments', 'phenotype_description',
        'phenotype_mim_number', 'phenotype_map_method', 'phenotype_inheritance',
        'chrom', 'start', 'end',
    ]
    CACHED_RECORDS_BUCKET = 'seqr-reference-data/omim'
    CACHED_RECORDS_FILENAME = 'parsed_omim_records__latest'
    CACHED_OMIM_URL = f'https://storage.googleapis.com/{CACHED_RECORDS_BUCKET}/{CACHED_RECORDS_FILENAME}.txt'

    MAP_METHOD_CHOICES = (
        ('1', 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.'),
        ('2', 'the disorder has been placed on the map by linkage; no mutation has been found.'),
        ('3', 'the molecular basis for the disorder is known; a mutation has been found in the gene.'),
        ('4', 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.'),
    )

    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE, null=True, blank=True)

    chrom = models.CharField(max_length=2)
    start = models.IntegerField()
    end = models.IntegerField()

    mim_number = models.IntegerField()  # Example: 601365
    gene_description = models.TextField(null=True, blank=True)  # Example: "Dishevelled 1 (homologous to Drosophila dsh)"
    comments = models.TextField(null=True, blank=True)  # Example: "associated with rs10492972"
    phenotype_inheritance = models.TextField(null=True, blank=True)  # Example: "Autosomal dominant"
    phenotype_mim_number = models.IntegerField(null=True, blank=True)  # Example: 616331
    phenotype_description = models.TextField(null=True, blank=True)  # Example: "Robinow syndrome, autosomal dominant 2"
    phenotype_map_method = models.CharField(max_length=1, choices=MAP_METHOD_CHOICES, null=True, blank=True)  # Example: 2

    class Meta:
        # ('mim_number', 'phenotype_mim_number') is not unique - for example ('124020', '609535')
        unique_together = ('mim_number', 'phenotype_mim_number', 'phenotype_description')

        json_fields = ['mim_number', 'phenotype_mim_number', 'phenotype_description', 'phenotype_inheritance',
                       'chrom', 'start', 'end',]

    @classmethod
    def get_url(cls, omim_key=None, **kwargs):
        return cls.OMIM_URL.format(omim_key=omim_key) if omim_key else cls.CACHED_OMIM_URL

    @classmethod
    def get_current_version(cls, **kwargs):
        return cls._get_file_last_modified(**kwargs)

    @staticmethod
    def get_file_header(f):
        header_fields = None
        for i, line in enumerate(f):
            line = line.rstrip('\r\n')
            split_line = line.split('\t')
            if split_line == Omim.CACHED_RECORDS_HEADER:
                return split_line
            if line.startswith("# Chrom") and header_fields is None:
                header_fields = [c.lower().replace(' ', '_') for c in split_line]
                break
            elif not line or line.startswith("#"):
                continue
            elif 'account is inactive' in line or 'account has expired' in line:
                raise ValueError(line)
            elif header_fields is None:
                raise ValueError("Header row not found in genemap2 file before line {}: {}".format(i, line))

        return header_fields

    @classmethod
    def parse_record(cls, record, omim_key=None, gene_ids_to_gene=None, gene_symbols_to_gene=None, **kwargs):
        if not omim_key:
            output_record = {k: v or None for k, v in record.items()}
            output_record['gene_id'] = gene_ids_to_gene.get(output_record.pop('ensembl_gene_id'))
            yield output_record
        # skip commented rows
        elif len(record) == 1:
            yield None
        else:
            gene_symbol = record['approved_gene_symbol'].strip() or record['gene/locus_and_other_related_symbols'].split(",")[0]
            ensembl_gene_id = record['ensembl_gene_id'] or gene_symbols_to_gene.get(gene_symbol)
            gene_id = gene_ids_to_gene.get(ensembl_gene_id)

            phenotype_field = record['phenotypes'].strip()

            record_with_phenotype = None
            for phenotype_match in re.finditer("[\[{ ]*(.+?)[ }\]]*(, (\d{4,}))? \(([1-4])\)(, ([^;]+))?;?",
                                               phenotype_field):
                # Phenotypes example: "Langer mesomelic dysplasia, 249700 (3), Autosomal recessive; Leri-Weill dyschondrosteosis, 127300 (3), Autosomal dominant"
                record_with_phenotype = cls._get_parsed_record(record, gene_id, ensembl_gene_id, phenotype_match)
                yield record_with_phenotype

            if record_with_phenotype is None:
                if len(phenotype_field) > 0:
                    raise ValueError("No phenotypes found: {}".format(json.dumps(record)))
                elif not gene_id:
                    # OMIM record requires either gene or phenotype
                    yield None
                else:
                    yield cls._get_parsed_record(record, gene_id, ensembl_gene_id)

    @staticmethod
    def _get_parsed_record(record, gene_id, ensembl_gene_id, phenotype_match=None):
        output_record = {
            'gene_id': gene_id,
            'ensembl_gene_id': ensembl_gene_id,
            'mim_number': int(record['mim_number']),
            'chrom': record['#_chromosome'].replace('chr', ''),
            'start': int(record['genomic_position_start']),
            'end': int(record['genomic_position_end']),
            'gene_description': record['gene_name'],
            'comments': record['comments'],
        }
        if phenotype_match:
            output_record.update({
                'phenotype_description': phenotype_match.group(1),
                'phenotype_mim_number': int(phenotype_match.group(3)) if phenotype_match.group(3) else None,
                'phenotype_map_method': phenotype_match.group(4),
                'phenotype_inheritance': phenotype_match.group(6) or None,
            })

        return output_record

    @classmethod
    def get_record_models(cls, records, omim_key=None, **kwargs):
        if omim_key:
            write_multiple_files(
                [(cls.CACHED_RECORDS_FILENAME, cls.CACHED_RECORDS_HEADER, records)],
                f'gs://{cls.CACHED_RECORDS_BUCKET}', file_format='txt', user=None,
            )
            for record in records:
                del record['ensembl_gene_id']
        return super().get_record_models(records, **kwargs)

# based on dbNSFPv3.5a_gene fields
class dbNSFPGene(GeneMetadataModel):

    CURRENT_VERSION = 'dbNSFP4.0_gene'
    URL = f'http://storage.googleapis.com/seqr-reference-data/dbnsfp/{CURRENT_VERSION}'

    gene_names = models.TextField(blank=True)

    function_desc = models.TextField(null=True, blank=True)
    disease_desc = models.TextField(null=True, blank=True)
    uniprot_acc = models.TextField(null=True, blank=True)
    uniprot_id = models.TextField(null=True, blank=True)
    entrez_gene_id = models.TextField(null=True, blank=True)
    ccds_id = models.TextField(null=True, blank=True)
    refseq_id = models.TextField(null=True, blank=True)
    ucsc_id = models.TextField(null=True, blank=True)
    pathway_uniprot = models.TextField(null=True, blank=True)
    pathway_biocarta_short = models.TextField(null=True, blank=True)  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
    pathway_biocarta_full = models.TextField(null=True, blank=True)    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
    pathway_consensus_path_db = models.TextField(null=True, blank=True)   # Pathway(s) the gene belongs to (from ConsensusPathDB)
    pathway_kegg_id = models.TextField(null=True, blank=True)           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
    pathway_kegg_full = models.TextField(null=True, blank=True)         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
    function_desc = models.TextField(null=True, blank=True)  # Function description of the gene (from Uniprot)
    disease_desc = models.TextField(null=True, blank=True)    # Disease(s) the gene caused or associated with (from Uniprot)
    trait_association_gwas = models.TextField(null=True, blank=True) # Trait(s) the gene associated with (from GWAS catalog)
    go_biological_process = models.TextField(null=True, blank=True)   # GO terms for biological process
    go_cellular_component = models.TextField(null=True, blank=True)   # GO terms for cellular component
    go_molecular_function = models.TextField(null=True, blank=True)   # GO terms for molecular function
    tissue_specificity = models.TextField(null=True, blank=True)   # Tissue specificity description from Uniprot
    expression_egenetics = models.TextField(null=True, blank=True)   # Tissues/organs the gene expressed in (egenetics data from BioMart)
    expression_gnf_atlas = models.TextField(null=True, blank=True)   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
    rvis_exac = models.TextField(null=True, blank=True)
    ghis = models.TextField(null=True, blank=True)
    essential_gene = models.TextField(null=True, blank=True)   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
    mgi_mouse_gene = models.TextField(null=True, blank=True)   # Homolog mouse gene name from MGI
    mgi_mouse_phenotype = models.TextField(null=True, blank=True)   # Phenotype description for the homolog mouse gene from MGI
    zebrafish_gene = models.TextField(null=True, blank=True)   # Homolog zebrafish gene name from ZFIN
    zebrafish_structure = models.TextField(null=True, blank=True)   # Affected structure of the homolog zebrafish gene from ZFIN
    zebrafish_phenotype_quality = models.TextField(null=True, blank=True)   # Phenotype description for the homolog zebrafish gene from ZFIN
    zebrafish_phenotype_tag = models.TextField(null=True, blank=True)   # Phenotype tag for the homolog zebrafish gene from ZFIN

    class Meta:
        json_fields = ['function_desc', 'disease_desc', 'gene_names']

    @staticmethod
    def parse_gene_record(record):
        parsed_record = {DBNSFP_FIELD_MAP.get(k, k.split('(')[0].lower()): (v if v != '.' else '')
                         for k, v in record.items() if not k.startswith(DBNSFP_EXCLUDE_FIELDS)}
        parsed_record["function_desc"] = parsed_record["function_desc"].replace("FUNCTION: ", "")
        parsed_record['gene_id'] = parsed_record['gene_id'].split(';')[0]
        if not parsed_record['gene_id']:
            return None

        gene_names = [record['Gene_name']]
        for gene_name_key in ['Gene_old_names', 'Gene_other_names']:
            names = record[gene_name_key] if record[gene_name_key] != '.' else ''
            gene_names += names.split(';')
        parsed_record['gene_names'] = ';'.join([name for name in gene_names if name])

        return parsed_record

class PrimateAI(GeneMetadataModel):

    CURRENT_VERSION = 'cleaned_v0.2'
    URL = f'http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.{CURRENT_VERSION}.txt'

    percentile_25 = models.FloatField()
    percentile_75 = models.FloatField()

    class Meta:
        json_fields = ['percentile_25', 'percentile_75']

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_symbol': record['genesymbol'],
            'percentile_25': float(record['pcnt25']),
            'percentile_75': float(record['pcnt75']),
        }


class MGI(GeneMetadataModel):

    CURRENT_VERSION = 'HMD_HumanPhenotype'
    URL = f'https://storage.googleapis.com/seqr-reference-data/mgi/{CURRENT_VERSION}.rpt.txt'

    marker_id = models.CharField(max_length=15)

    class Meta:
        unique_together = ('gene', 'marker_id')
        json_fields = ['marker_id']

    @staticmethod
    def get_file_header(f):
        return ['gene_symbol', 'entrez_gene_id', 'mouse_gene_symbol', 'marker_id', 'phenotype_ids']

    @staticmethod
    def parse_gene_record(record):
        return {k: v.strip() for k, v in record.items() if k in ['gene_symbol', 'marker_id', 'entrez_gene_id']}

    @classmethod
    def update_records(cls, **kwargs):
        entrez_id_to_gene = dict(dbNSFPGene.objects.values_list('entrez_gene_id', 'gene_id'))
        super().update_records(entrez_id_to_gene=entrez_id_to_gene, **kwargs)

    @classmethod
    def get_gene_for_record(cls, record, *args, entrez_id_to_gene=None, **kwargs):
        entrez_gene = entrez_id_to_gene.get(record.pop('entrez_gene_id'))
        gene = super().get_gene_for_record(record, *args, **kwargs)
        return gene or entrez_gene


class GenCC(GeneMetadataModel):

    URL = 'https://search.thegencc.org/download/action/submissions-export-csv'
    CLASSIFICATION_FIELDS = {
        'disease_title': 'disease',
        'classification_title': 'classification',
        'moi_title': 'moi',
        'submitter_title': 'submitter',
        'submitted_as_date': 'date',
    }

    hgnc_id = models.CharField(max_length=10)
    classifications = models.JSONField()

    class Meta:
        json_fields = ['classifications', 'hgnc_id']

    @classmethod
    def get_current_version(cls, **kwargs):
        return cls._get_file_last_modified(**kwargs)

    @staticmethod
    def get_file_header(f):
        return [k.replace('"', '') for k in next(f).rstrip('\n\r').split(',')]

    @classmethod
    def get_file_iterator(cls, f):
        return super().get_file_iterator(csv.reader(f))

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_symbol': record['gene_symbol'],
            'hgnc_id': record['gene_curie'],
            'classifications': [{title: record[field] for field, title in GenCC.CLASSIFICATION_FIELDS.items()}]
        }

    @classmethod
    def get_record_models(cls, records, **kwargs):
        #  Group all classifications for a gene into a single model
        records_by_gene = {}
        for record in records:
            if record['gene_id'] in records_by_gene:
                records_by_gene[record['gene_id']]['classifications'] += record['classifications']
            else:
                records_by_gene[record['gene_id']] = record

        return super().get_record_models(records_by_gene.values(), **kwargs)


class ClinGen(GeneMetadataModel):

    URL = 'https://search.clinicalgenome.org/kb/gene-dosage/download'

    haploinsufficiency = models.TextField()
    triplosensitivity = models.TextField()
    href = models.TextField()

    class Meta:
        json_fields = ['haploinsufficiency', 'triplosensitivity', 'href']

    @classmethod
    def get_current_version(cls, **kwargs):
        file_path = download_file(cls.get_url(**kwargs))
        with open(file_path, 'r') as f:
            csv_f = csv.reader(f)
            created_meta_row = next(row for row in csv_f if row[0].startswith('FILE CREATED'))
            return created_meta_row[0].split(':')[-1].strip()

    @staticmethod
    def get_file_header(f):
        csv_f = csv.reader(f)
        next(row for row in csv_f if all(ch == '+' for ch in row[0])) # iterate past the metadata info
        header_line = next(csv_f)
        next(csv_f) # there is another padding row before the content starts

        return [col.replace(' ', '_').lower() for col in header_line]

    @classmethod
    def get_file_iterator(cls, f):
        return super().get_file_iterator(csv.reader(f))

    @staticmethod
    def parse_gene_record(record):
        return {
            'gene_symbol': record['gene_symbol'],
            'haploinsufficiency': record['haploinsufficiency'].replace(' for Haploinsufficiency', ''),
            'triplosensitivity': record['triplosensitivity'].replace(' for Triplosensitivity', ''),
            'href': record['online_report'],
        }

class DataVersions(models.Model):
    data_model_name = models.CharField(max_length=30, primary_key=True)
    version = models.CharField(max_length=40)