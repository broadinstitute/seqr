import csv
from django.db import models, transaction
import gzip
import logging
from tqdm import tqdm

from reference_data.utils.dbnsfp_utils import DBNSFP_FIELD_MAP, DBNSFP_EXCLUDE_FIELDS
from reference_data.utils.download_utils import download_file

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
    def get_current_version(cls):
        return cls.CURRENT_VERSION

    @classmethod
    def parse_record(cls, record, **kwargs):
        raise NotImplementedError

    @staticmethod
    def get_file_header(f):
        return next(f).rstrip('\n\r').split('\t')

    @classmethod
    def get_file_iterator(cls, f):
        return tqdm(f, unit=' records')

    @staticmethod
    def post_process_models(models):
        pass

    @classmethod
    def update_records(cls, **kwargs):
        missing_mappings = {k for k, v in kwargs.items() if not v}
        if missing_mappings:
            raise ValueError(f'Related data is missing to load {cls.__name__}: {", ".join(sorted(missing_mappings))}')

        logger.info(f'Updating {cls.__name__}')

        file_path = download_file(cls.URL)

        models = []
        logger.info('Parsing file')
        open_file = gzip.open if file_path.endswith('.gz') else open
        open_mode = 'rt' if file_path.endswith('.gz') else 'r'
        with open_file(file_path, open_mode) as f:
            header_fields = cls.get_file_header(f)

            for line in cls.get_file_iterator(f):
                record = dict(zip(header_fields, line if isinstance(line, list) else line.rstrip('\r\n').split('\t')))
                for record in cls.parse_record(record, **kwargs):
                    if record is None:
                        continue
                    models.append(cls(**record))

        cls.post_process_models(models)

        with transaction.atomic():
            deleted = cls.objects.all().delete()
            logger.info(f'Deleted {deleted} {cls.__name__} records')
            cls.objects.bulk_create(models)
            logger.info(f'Created {len(models)} {cls.__name__} records')

        logger.info('Done')
        logger.info(f'Loaded {cls.objects.count()} {cls.__name__} records from {file_path}')


class HumanPhenotypeOntology(LoadableModel):
    """Human Phenotype Ontology table contains one record per phenotype term parsed from the hp.obo
    file at http://human-phenotype-ontology.github.io/downloads.html
    """
    hpo_id = models.CharField(max_length=20, null=False, blank=False, unique=True, db_index=True)
    parent_id = models.CharField(max_length=20, null=True, blank=True)
    # hpo id of top-level phenotype category (eg. 'cardiovascular')
    category_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    # whether this hpo id is itself one of the top-level categories (eg. 'cardiovascular')
    is_category = models.BooleanField(default=False, db_index=True)

    name = models.TextField(null=False, blank=False)

    definition = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)


class GeneInfo(LoadableModel):
    """Human gene models from https://www.gencodegenes.org/releases/
    http://www.gencodegenes.org/gencodeformat.html
    """

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


class GeneMetadataModel(LoadableModel):

    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @classmethod
    def get_gene_for_record(cls, record, gene_ids_to_gene=None, gene_symbols_to_gene=None, **kwargs):
        gene_id = record.pop('gene_id', None)
        gene_symbol = record.pop('gene_symbol', None)

        return gene_ids_to_gene.get(gene_id) or gene_symbols_to_gene.get(gene_symbol)

    @classmethod
    def parse_record(cls, record, skipped_genes=None, **kwargs):
        if record is not None:
            record['gene'] = cls.get_gene_for_record(record, **kwargs)
            if not record['gene']:
                skipped_genes[record['gene']] = True
                record = None
        yield record

    @classmethod
    def update_records(cls, **kwargs):
        skipped_genes = {-1: True}  # Include placeholder to prevent missing mapping validation failure
        super().update_records(skipped_genes=skipped_genes, **kwargs)
        del skipped_genes[-1]
        if skipped_genes:
            logger.info(f'Skipped {len(skipped_genes)} records with unrecognized genes.')


class TranscriptInfo(GeneMetadataModel):
    # TODO is not loaded like other GeneMetadataModels

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


class RefseqTranscript(LoadableModel):
    transcript = models.OneToOneField(TranscriptInfo, on_delete=models.CASCADE)
    refseq_id = models.CharField(max_length=20)


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

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
            'gene_id': record['gene_id'].split(".")[0],
            'gene_symbol': record['gene'],
            'mis_z': float(record['mis_z']) if record['mis_z'] != 'NaN' else -100,
            'pLI': float(record['pLI']) if record['pLI'] != 'NA' else 0,
            'louef': float(record['oe_lof_upper']) if record['oe_lof'] != 'NA' else 100,
        }

    @staticmethod
    def post_process_models(models):
        # add _rank fields
        for field, order in [('mis_z', -1), ('pLI', -1), ('louef', 1)]:
            for i, model in enumerate(sorted(models, key=lambda model: order * getattr(model, field))):
                setattr(model, '{}_rank'.format(field), i)


class GeneCopyNumberSensitivity(GeneMetadataModel):

    CURRENT_VERSION = 'Collins_rCNV_2022'
    URL = f'https://zenodo.org/record/6347673/files/{CURRENT_VERSION}.dosage_sensitivity_scores.tsv.gz'

    pHI = models.FloatField()
    pTS = models.FloatField()

    class Meta:
        json_fields = ['pHI', 'pTS']

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
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

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
            'gene_id': record['ensg'],
            'post_mean': float(record['post_mean']),
        }


class Omim(LoadableModel):
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

    @classmethod
    def parse_record(cls, record, **kwargs):
        parsed_record = {DBNSFP_FIELD_MAP.get(k, k.split('(')[0].lower()): (v if v != '.' else '')
                         for k, v in record.items() if not k.startswith(DBNSFP_EXCLUDE_FIELDS)}
        parsed_record["function_desc"] = parsed_record["function_desc"].replace("FUNCTION: ", "")
        parsed_record['gene_id'] = parsed_record['gene_id'].split(';')[0]

        gene_names = [record['Gene_name']]
        for gene_name_key in ['Gene_old_names', 'Gene_other_names']:
            names = record[gene_name_key] if record[gene_name_key] != '.' else ''
            gene_names += names.split(';')
        parsed_record['gene_names'] = ';'.join([name for name in gene_names if name])

        if parsed_record['gene_id']:
            yield parsed_record
        else:
            yield None


class PrimateAI(GeneMetadataModel):

    CURRENT_VERSION = 'cleaned_v0.2'
    URL = f'http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.{CURRENT_VERSION}.txt'

    percentile_25 = models.FloatField()
    percentile_75 = models.FloatField()

    class Meta:
        json_fields = ['percentile_25', 'percentile_75']

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
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

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {k: v.strip() for k, v in record.items() if k in ['gene_symbol', 'marker_id', 'entrez_gene_id']}

    @classmethod
    def update_records(cls, **kwargs):
        entrez_id_to_gene = {
            dbnsfp.entrez_gene_id: dbnsfp.gene for dbnsfp in dbNSFPGene.objects.all().prefetch_related('gene')
        }
        super().update_records(entrez_id_to_gene=entrez_id_to_gene, **kwargs)

    @classmethod
    def get_gene_for_record(cls, record, entrez_id_to_gene=None, **kwargs):
        entrez_gene = entrez_id_to_gene.get(record.pop('entrez_gene_id'))

        try:
            return super().get_gene_for_record(record, **kwargs)
        except ValueError as e:
            if entrez_gene:
                return entrez_gene
            raise e


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
    def get_current_version(cls):
        # GenCC updates regularly and does not have versioned data
        raise NotImplementedError

    @staticmethod
    def get_file_header(f):
        return [k.replace('"', '') for k in next(f).rstrip('\n\r').split(',')]

    @classmethod
    def get_file_iterator(cls, f):
        return super().get_file_iterator(csv.reader(f))

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
            'gene_symbol': record['gene_symbol'],
            'hgnc_id': record['gene_curie'],
            'classifications': [{title: record[field] for field, title in cls.CLASSIFICATION_FIELDS.items()}]
        }

    @staticmethod
    def post_process_models(models):
        #  Group all classifications for a gene into a single model
        models_by_gene = {}
        for model in tqdm(models, unit=' models'):
            if model.gene in models_by_gene:
                models_by_gene[model.gene].classifications += model.classifications
            else:
                models_by_gene[model.gene] = model

        models.clear()
        models.extend(models_by_gene.values())


class ClinGen(GeneMetadataModel):

    URL = 'https://search.clinicalgenome.org/kb/gene-dosage/download'

    haploinsufficiency = models.TextField()
    triplosensitivity = models.TextField()
    href = models.TextField()

    class Meta:
        json_fields = ['haploinsufficiency', 'triplosensitivity', 'href']

    @classmethod
    def get_current_version(cls):
        # ClinGen updates regularly and does not have versioned data
        raise NotImplementedError

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

    @classmethod
    def parse_record(cls, record, **kwargs):
        yield {
            'gene_symbol': record['gene_symbol'],
            'haploinsufficiency': record['haploinsufficiency'].replace(' for Haploinsufficiency', ''),
            'triplosensitivity': record['triplosensitivity'].replace(' for Triplosensitivity', ''),
            'href': record['online_report'],
        }