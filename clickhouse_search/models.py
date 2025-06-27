from clickhouse_backend import models

from django.db.migrations import state
from django.db.models import options, ForeignKey, OneToOneField, Func, CASCADE, PROTECT

from clickhouse_search.backend.engines import CollapsingMergeTree, EmbeddedRocksDB, Join
from clickhouse_search.backend.fields import Enum8Field, NestedField, UInt64FieldDeltaCodecField, NamedTupleField
from clickhouse_search.managers import EntriesManager, AnnotationsQuerySet
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample
from seqr.utils.search.constants import SPLICE_AI_FIELD
from seqr.utils.xpos_utils import CHROMOSOMES
from settings import CLICKHOUSE_IN_MEMORY_DIR, CLICKHOUSE_DATA_DIR

options.DEFAULT_NAMES = (
    *options.DEFAULT_NAMES,
    'projection',
)
state.DEFAULT_NAMES = options.DEFAULT_NAMES


class ClickHouseRouter:
    """
    Adapted from https://github.com/jayvynl/django-clickhouse-backend/blob/v1.3.2/README.md#configuration
    """

    def __init__(self):
        self.route_model_names = set()
        for model in self._get_subclasses(models.ClickhouseModel):
            if model._meta.abstract:
                continue
            self.route_model_names.add(model._meta.label_lower)

    @staticmethod
    def _get_subclasses(class_):
        classes = class_.__subclasses__()

        index = 0
        while index < len(classes):
            classes.extend(classes[index].__subclasses__())
            index += 1

        return list(set(classes))

    def db_for_read(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if f'{app_label}.{model_name}' in self.route_model_names  or hints.get('clickhouse'):
            return db == 'clickhouse'
        elif db == 'clickhouse':
            return False
        return None


class Projection(Func):

    def __init__(self, name, select='*', order_by=None):
        self.name = name
        self.select = select
        self.order_by = order_by


class BaseAnnotations(models.ClickhouseModel):

    CHROMOSOME_CHOICES = [(i+1, chrom) for i, chrom in enumerate(CHROMOSOMES)]
    SEQR_POPULATIONS = [
        ('seqr', {'ac': 'ac', 'hom': 'hom'}),
    ]
    ANNOTATION_CONSTANTS = {
        'genomeVersion': GENOME_VERSION_GRCh38,
        'liftedOverGenomeVersion': GENOME_VERSION_GRCh37,
    }

    key = models.UInt32Field(primary_key=True)
    xpos = models.UInt64Field()
    pos = models.UInt32Field()
    variant_id = models.StringField(db_column='variantId')
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)

    objects = AnnotationsQuerySet.as_manager()

    class Meta:
        abstract = True

class BaseAnnotationsMitoSnvIndel(BaseAnnotations):
    CONSEQUENCE_TERMS = [(1, 'transcript_ablation'), (2, 'splice_acceptor_variant'), (3, 'splice_donor_variant'), (4, 'stop_gained'), (5, 'frameshift_variant'), (6, 'stop_lost'), (7, 'start_lost'), (8, 'inframe_insertion'), (9, 'inframe_deletion'), (10, 'missense_variant'), (11, 'protein_altering_variant'), (12, 'splice_donor_5th_base_variant'), (13, 'splice_region_variant'), (14, 'splice_donor_region_variant'), (15, 'splice_polypyrimidine_tract_variant'), (16, 'incomplete_terminal_codon_variant'), (17, 'start_retained_variant'), (18, 'stop_retained_variant'), (19, 'synonymous_variant'), (20, 'coding_sequence_variant'), (21, 'mature_miRNA_variant'), (22, '5_prime_UTR_variant'), (23, '3_prime_UTR_variant'), (24, 'non_coding_transcript_exon_variant'), (25, 'intron_variant'), (26, 'NMD_transcript_variant'), (27, 'non_coding_transcript_variant'), (28, 'coding_transcript_variant'), (29, 'upstream_gene_variant'), (30, 'downstream_gene_variant'), (31, 'intergenic_variant'), (32, 'sequence_variant')]
    MUTATION_TASTER_PREDICTIONS = [(0, 'D'), (1, 'A'), (2, 'N'), (3, 'P')]
    TRANSCRIPTS_FIELDS = [
        ('aminoAcids', models.StringField(null=True, blank=True)),
        ('biotype', models.StringField(null=True, blank=True)),
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('codons', models.StringField(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=CONSEQUENCE_TERMS))),
        ('geneId', models.StringField(null=True, blank=True)),
        ('hgvsc', models.StringField(null=True, blank=True)),
        ('hgvsp', models.StringField(null=True, blank=True)),
        ('loftee', NamedTupleField([
            ('isLofNagnag', models.BoolField(null=True, blank=True)),
            ('lofFilters', models.ArrayField(models.StringField(null=True, blank=True))),
        ], null_empty_arrays=True)),
        ('majorConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=CONSEQUENCE_TERMS)),
        ('transcriptId', models.StringField()),
        ('transcriptRank', models.UInt8Field()),
    ]

    ref = models.StringField()
    alt = models.StringField()
    rsid = models.StringField(null=True, blank=True)

    class Meta:
        abstract = True

class BaseAnnotationsSvGcnv(BaseAnnotations):
    SV_CONSEQUENCE_RANKS = [(1,'LOF'), (2,'INTRAGENIC_EXON_DUP'), (3,'PARTIAL_EXON_DUP'), (4,'COPY_GAIN'), (5,'DUP_PARTIAL'), (6,'MSV_EXON_OVERLAP'), (7,'INV_SPAN'), (8,'UTR'), (9,'PROMOTER'), (10,'TSS_DUP'), (11,'BREAKEND_EXONIC'), (12,'INTRONIC'), (13,'NEAREST_TSS'),]
    SV_TYPES =  [(1,'gCNV_DEL'), (2,'gCNV_DUP'), (3,'BND'), (4,'CPX'), (5,'CTX'), (6,'DEL'), (7,'DUP'), (8,'INS'), (9,'INV'), (10,'CNV')]
    PREDICTION_FIELDS = [
        ('strvctvre', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    SORTED_GENE_CONSQUENCES_FIELDS = [
        ('geneId', models.StringField(null=True, blank=True)),
        ('majorConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=SV_CONSEQUENCE_RANKS)),
    ]

    chrom = Enum8Field(return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES)
    end = models.UInt32Field()
    rg37_locus_end = NamedTupleField([
        ('contig', models.Enum8Field(return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES, null=True, blank=True)),
        ('position', models.UInt32Field(null=True, blank=True)),
    ], db_column='rg37LocusEnd', null_if_empty=True)
    lifted_over_chrom = Enum8Field(db_column='liftedOverChrom', return_int=False, null=True, blank=True, choices=BaseAnnotations.CHROMOSOME_CHOICES)
    sv_type = models.Enum8Field(db_column='svType', return_int=False, choices=SV_TYPES)
    predictions = NamedTupleField(PREDICTION_FIELDS)
    sorted_gene_consequences = NestedField(SORTED_GENE_CONSQUENCES_FIELDS, db_column='sortedTranscriptConsequences')

    class Meta:
        abstract = True


class BaseAnnotationsGRCh37SnvIndel(BaseAnnotationsMitoSnvIndel):
    ANNOTATION_CONSTANTS = {
        'genomeVersion': GENOME_VERSION_GRCh37,
        'liftedOverGenomeVersion': GENOME_VERSION_GRCh38,
    }
    POPULATION_FIELDS = [
        ('exac', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_exomes', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_genomes', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('topmed', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
    ]
    PREDICTION_FIELDS = [
        ('cadd', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('eigen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('fathmm', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mpc', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_pred', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_taster', models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseAnnotationsMitoSnvIndel.MUTATION_TASTER_PREDICTIONS)),
        ('polyphen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('primate_ai', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('revel', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('sift', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        (SPLICE_AI_FIELD, models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('splice_ai_consequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'Acceptor gain'), (1, 'Acceptor loss'), (2, 'Donor gain'), (3, 'Donor loss'), (4, 'No consequence')])),
        ('vest', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    HGMD_CLASSES = [(0, 'DM'), (1, 'DM?'), (2, 'DP'), (3, 'DFP'), (4, 'FP'), (5, 'R')]
    SORTED_TRANSCRIPT_CONSQUENCES_FIELDS = [
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseAnnotationsMitoSnvIndel.CONSEQUENCE_TERMS))),
        ('geneId', models.StringField(null=True, blank=True))
    ]

    chrom = Enum8Field(return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES)
    lifted_over_chrom = Enum8Field(db_column='liftedOverChrom', return_int=False, null=True, blank=True, choices=BaseAnnotations.CHROMOSOME_CHOICES)
    caid = models.StringField(db_column='CAID', null=True, blank=True)
    hgmd = NamedTupleField([
        ('accession', models.StringField(null=True, blank=True)),
        ('classification', models.Enum8Field(null=True, blank=True, return_int=False, choices=HGMD_CLASSES)),
    ], null_if_empty=True, rename_fields={'classification': 'class'})
    predictions = NamedTupleField(PREDICTION_FIELDS)
    populations = NamedTupleField(POPULATION_FIELDS)
    sorted_transcript_consequences = NestedField(SORTED_TRANSCRIPT_CONSQUENCES_FIELDS, db_column='sortedTranscriptConsequences')

    class Meta:
        abstract = True

class AnnotationsGRCh37SnvIndel(BaseAnnotationsGRCh37SnvIndel):

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh37/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)

class AnnotationsDiskGRCh37SnvIndel(BaseAnnotationsGRCh37SnvIndel):

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)

class BaseAnnotationsSnvIndel(BaseAnnotationsGRCh37SnvIndel):
    ANNOTATION_CONSTANTS = BaseAnnotations.ANNOTATION_CONSTANTS
    PREDICTION_FIELDS = sorted([
        ('gnomad_noncoding', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        *BaseAnnotationsGRCh37SnvIndel.PREDICTION_FIELDS,
    ])
    SORTED_TRANSCRIPT_CONSQUENCES_FIELDS = sorted([
        ('alphamissensePathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ('extendedIntronicSpliceRegionVariant', models.BoolField(null=True, blank=True)),
        ('fiveutrConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(1, '5_prime_UTR_premature_start_codon_gain_variant'), (2, '5_prime_UTR_premature_start_codon_loss_variant'), (3, '5_prime_UTR_stop_codon_gain_variant'), (4, '5_prime_UTR_stop_codon_loss_variant'), (5, '5_prime_UTR_uORF_frameshift_variant')])),
        *BaseAnnotationsGRCh37SnvIndel.SORTED_TRANSCRIPT_CONSQUENCES_FIELDS,
    ])

    screen_region_type = Enum8Field(db_column='screenRegionType', null=True, blank=True, return_int=False, choices=[(0, 'CTCF-bound'), (1, 'CTCF-only'), (2, 'DNase-H3K4me3'), (3, 'PLS'), (4, 'dELS'), (5, 'pELS'), (6, 'DNase-only'), (7, 'low-DNase')])
    predictions = NamedTupleField(PREDICTION_FIELDS)
    sorted_transcript_consequences = NestedField(SORTED_TRANSCRIPT_CONSQUENCES_FIELDS, db_column='sortedTranscriptConsequences')
    sorted_motif_feature_consequences = NestedField([
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'TFBS_ablation'), (1, 'TFBS_amplification'), (2, 'TF_binding_site_variant'), (3, 'TFBS_fusion'), (4, 'TFBS_translocation')]))),
        ('motifFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedMotifFeatureConsequences', null_when_empty=True)
    sorted_regulatory_feature_consequences = NestedField([
        ('biotype', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'enhancer'), (1, 'promoter'), (2, 'CTCF_binding_site'), (3, 'TF_binding_site'), (4, 'open_chromatin_region')])),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'regulatory_region_ablation'), (1, 'regulatory_region_amplification'), (2, 'regulatory_region_variant'), (3, 'regulatory_region_fusion')]))),
        ('regulatoryFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedRegulatoryFeatureConsequences', null_when_empty=True)

    class Meta:
        abstract = True

class AnnotationsSnvIndel(BaseAnnotationsSnvIndel):

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)

class AnnotationsDiskSnvIndel(BaseAnnotationsSnvIndel):

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)

class BaseAnnotationsMito(BaseAnnotationsMitoSnvIndel):
    ANNOTATION_CONSTANTS = {
        'chrom': 'M',
        'liftedOverChrom': 'MT',
        **BaseAnnotations.ANNOTATION_CONSTANTS,
    }
    MITOTIP_PATHOGENICITIES = [
        (0, 'likely_pathogenic'),
        (1, 'possibly_pathogenic'),
        (2, 'possibly_benign'),
        (3, 'likely_benign'),
    ]
    POPULATION_FIELDS = [
        ('gnomad_mito', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
        ])),
        ('gnomad_mito_heteroplasmy', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('max_hl', models.DecimalField(max_digits=9, decimal_places=5)),
        ])),
        ('helix', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
        ])),
        ('helix_heteroplasmy', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('max_hl', models.DecimalField(max_digits=9, decimal_places=5)),
        ])),
    ]
    PREDICTION_FIELDS = [
        ('apogee', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('haplogroup_defining', models.BoolField(null=True, blank=True)),
        ('hmtvar', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mitotip', models.Enum8Field(null=True, blank=True, return_int=False, choices=MITOTIP_PATHOGENICITIES)),
        ('mut_taster', models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseAnnotationsMitoSnvIndel.MUTATION_TASTER_PREDICTIONS)),
        ('sift', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mlc', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    SEQR_POPULATIONS = [
        ('seqr', {'ac': 'ac_hom'}),
        ('seqr_heteroplasmy', {'ac': 'ac_het'}),
    ]

    common_low_heteroplasmy = models.BoolField(db_column='commonLowHeteroplasmy', null=True, blank=True)
    mitomap_pathogenic  = models.BoolField(db_column='mitomapPathogenic', null=True, blank=True)
    predictions = NamedTupleField(PREDICTION_FIELDS)
    populations = NamedTupleField(POPULATION_FIELDS)
    sorted_transcript_consequences = NestedField(BaseAnnotationsMitoSnvIndel.TRANSCRIPTS_FIELDS, db_column='sortedTranscriptConsequences', group_by_key='geneId')

    class Meta:
        abstract = True

class AnnotationsMito(BaseAnnotationsMito):

    class Meta:
        db_table = 'GRCh38/MITO/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/MITO/annotations', primary_key='key', flatten_nested=0)

class AnnotationsDiskMito(BaseAnnotationsMito):

    class Meta:
        db_table = 'GRCh38/MITO/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/MITO/annotations', primary_key='key', flatten_nested=0)


class BaseAnnotationsSv(BaseAnnotationsSvGcnv):
    POPULATION_FIELDS = [
        ('gnomad_svs', NamedTupleField([
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
            ('id', models.StringField()),
        ])),
    ]
    SV_TYPE_DETAILS = [(1, 'INS_iDEL'),(2, 'INVdel'),(3, 'INVdup'),(4, 'ME'),(5, 'ME:ALU'),(6, 'ME:LINE1'),(7, 'ME:SVA'),(8, 'dDUP'),(9, 'dDUP_iDEL'),(10, 'delINV'),(11, 'delINVdel'),(12, 'delINVdup'),(13, 'dupINV'),(14, 'dupINVdel'),(15, 'dupINVdup')]

    algorithms = models.StringField(low_cardinality=True)
    bothsides_support = models.BoolField(db_column='bothsidesSupport')
    cpx_intervals = NestedField([
        ('chrom', models.Enum8Field(return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES)),
        ('start', models.UInt32Field()),
        ('end', models.UInt32Field()),
        ('type', models.Enum8Field(return_int=False, choices=BaseAnnotationsSvGcnv.SV_TYPES)),
    ], db_column='cpxIntervals', null_when_empty=True)
    end_chrom = models.Enum8Field(db_column='endChrom', return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES, null=True, blank=True)
    sv_source_detail = NestedField(
        [('chrom', models.Enum8Field(return_int=False, choices=BaseAnnotations.CHROMOSOME_CHOICES, null=True, blank=True))],
        db_column='svSourceDetail',
        null_when_empty=True
    )
    sv_type_detail = models.Enum8Field(db_column='svTypeDetail', return_int=False, choices=SV_TYPE_DETAILS, null=True, blank=True)
    populations = NamedTupleField(POPULATION_FIELDS)

    class Meta:
        abstract = True

class AnnotationsSv(BaseAnnotationsSv):

    class Meta:
        db_table = 'GRCh38/SV/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SV/annotations', primary_key='key', flatten_nested=0)

class AnnotationsDiskSv(BaseAnnotationsSv):

    class Meta:
        db_table = 'GRCh38/SV/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SV/annotations', primary_key='key', flatten_nested=0)

class BaseAnnotationsGcnv(BaseAnnotationsSvGcnv):
    POPULATION_FIELDS = [
        ('seqrPop', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
    ]

    num_exon = models.UInt16Field(db_column='numExon')
    populations = NamedTupleField(POPULATION_FIELDS)

    class Meta:
        abstract = True

class AnnotationsGcnv(BaseAnnotationsGcnv):

    class Meta:
        db_table = 'GRCh38/GCNV/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/GCNV/annotations', primary_key='key', flatten_nested=0)

class AnnotationsDiskGcnv(BaseAnnotationsGcnv):

    class Meta:
        db_table = 'GRCh38/GCNV/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/GCNV/annotations', primary_key='key', flatten_nested=0)


class BaseClinvar(models.ClickhouseModel):

    PATHOGENICITY_CHOICES = list(enumerate([
        'Pathogenic', 'Pathogenic/Likely_pathogenic', 'Pathogenic/Likely_pathogenic/Established_risk_allele',
        'Pathogenic/Likely_pathogenic/Likely_risk_allele', 'Pathogenic/Likely_risk_allele', 'Likely_pathogenic', 'Likely_pathogenic/Likely_risk_allele',
        'Established_risk_allele', 'Likely_risk_allele', 'Conflicting_classifications_of_pathogenicity',
        'Uncertain_risk_allele', 'Uncertain_significance/Uncertain_risk_allele', 'Uncertain_significance',
        'No_pathogenic_assertion', 'Likely_benign', 'Benign/Likely_benign', 'Benign'
    ]))
    allele_id = models.UInt32Field(db_column='alleleId', null=True, blank=True)
    conflicting_pathogenicities = NestedField([
        ('count', models.UInt16Field()),
        ('pathogenicity', models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)),
    ], db_column='conflictingPathogenicities', null_when_empty=True)
    gold_stars = models.UInt8Field(db_column='goldStars', null=True, blank=True)
    submitters = models.ArrayField(models.StringField())
    conditions = models.ArrayField(models.StringField())
    assertions = models.ArrayField(models.Enum8Field(choices=[(0, 'Affects'), (1, 'association'), (2, 'association_not_found'), (3, 'confers_sensitivity'), (4, 'drug_response'), (5, 'low_penetrance'), (6, 'not_provided'), (7, 'other'), (8, 'protective'), (9, 'risk_factor'), (10, 'no_classification_for_the_single_variant'), (11, 'no_classifications_from_unflagged_records')], return_int=False))
    pathogenicity = models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)

    def _save_table(
        self,
        raw=False,
        cls=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        # loaddata attempts to run an ALTER TABLE to update existing rows, but since JOIN tables can not be altered
        # this command fails so need to use the force_insert flag to run an INSERT instead
        return super()._save_table(
            raw=raw, cls=cls, force_insert=True, force_update=force_update, using=using, update_fields=update_fields,
        )

    class Meta:
        abstract = True
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

class ClinvarGRCh37SnvIndel(BaseClinvar):
    key = ForeignKey('EntriesGRCh37SnvIndel', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh37/SNV_INDEL/clinvar'

class ClinvarSnvIndel(BaseClinvar):
    key = ForeignKey('EntriesSnvIndel', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh38/SNV_INDEL/clinvar'

class ClinvarMito(BaseClinvar):
    key = ForeignKey('EntriesMito', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh38/MITO/clinvar'


class BaseEntries(models.ClickhouseModel):
    project_guid = models.StringField(low_cardinality=True)
    family_guid = models.StringField()
    xpos = UInt64FieldDeltaCodecField()
    filters = models.ArrayField(models.StringField(low_cardinality=True))
    sign = models.Int8Field()

    objects = EntriesManager()

    def _save_table(
        self,
        raw=False,
        cls=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        # loaddata attempts to run an ALTER TABLE to update existing rows, but since primary keys can not be altered
        # this command fails so need to use the force_insert flag to run an INSERT instead
        return super()._save_table(
            raw=raw, cls=cls, force_insert=True, force_update=force_update, using=using, update_fields=update_fields,
        )

    class Meta:
        abstract = True
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'key'),
            partition_by='project_guid',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )
        projection = Projection('xpos_projection', order_by='xpos')

class BaseEntriesSnvIndel(BaseEntries):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('gq', models.UInt8Field(null=True, blank=True)),
        ('ab', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('dp', models.UInt16Field(null=True, blank=True)),
    ]

    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    is_gnomad_gt_5_percent = models.BoolField()
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    class Meta:
        abstract = True
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'is_gnomad_gt_5_percent', 'sample_type', 'key'),
            partition_by='project_guid',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )
        projection = Projection('xpos_projection', order_by='xpos, is_gnomad_gt_5_percent')

class EntriesGRCh37SnvIndel(BaseEntriesSnvIndel):

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseEntriesSnvIndel.Meta):
        db_table = 'GRCh37/SNV_INDEL/entries'

class EntriesSnvIndel(BaseEntriesSnvIndel):

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/entries'

class EntriesMito(BaseEntries):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('dp', models.UInt16Field(null=True, blank=True)),
        ('hl', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mitoCn', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('contamination', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    class Meta(BaseEntries.Meta):
        db_table = 'GRCh38/MITO/entries'
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'sample_type', 'key'),
            partition_by='project_guid',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )

class EntriesSv(BaseEntries):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('cn', models.UInt8Field(null=True, blank=True)),
        ('gq', models.UInt8Field(null=True, blank=True)),
        ('newCall', models.BoolField(null=True, blank=True)),
        ('prevCall', models.BoolField(null=True, blank=True)),
        ('prevNumAlt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
    ]

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    class Meta(BaseEntries.Meta):
        db_table = 'GRCh38/SV/entries'

class EntriesGcnv(BaseEntries):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('cn', models.UInt8Field(null=True, blank=True)),
        ('qs', models.UInt16Field(null=True, blank=True)),
        ('defragged', models.BoolField(null=True, blank=True)),
        ('start', models.UInt32Field(null=True, blank=True)),
        ('end', models.UInt32Field(null=True, blank=True)),
        ('numExon', models.UInt16Field(null=True, blank=True)),
        ('geneIds',  models.ArrayField(models.StringField(null=True, blank=True))),
        ('newCall', models.BoolField(null=True, blank=True)),
        ('prevCall', models.BoolField(null=True, blank=True)),
        ('prevOverlap', models.BoolField(null=True, blank=True)),
    ]

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsGcnv', db_column='key', primary_key=True, on_delete=CASCADE)
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    class Meta:
        db_table = 'GRCh38/GCNV/entries'

class TranscriptsGRCh37SnvIndel(models.ClickhouseModel):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    transcripts = NestedField(BaseAnnotationsMitoSnvIndel.TRANSCRIPTS_FIELDS, group_by_key='geneId')

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/transcripts'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/transcripts', primary_key='key', flatten_nested=0)

class TranscriptsSnvIndel(models.ClickhouseModel):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    transcripts = NestedField(sorted([
        ('alphamissense', NamedTupleField([
            ('pathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ])),
        ('exon', NamedTupleField([
            ('index', models.Int32Field(null=True, blank=True)),
            ('total', models.Int32Field(null=True, blank=True)),
        ], null_if_empty=True)),
        ('intron', NamedTupleField([
            ('index', models.Int32Field(null=True, blank=True)),
            ('total', models.Int32Field(null=True, blank=True)),
        ], null_if_empty=True)),
        ('manePlusClinical', models.StringField(null=True, blank=True)),
        ('maneSelect', models.StringField(null=True, blank=True)),
        ('refseqTranscriptId', models.StringField(null=True, blank=True)),
        ('spliceregion', NamedTupleField([
            ('extended_intronic_splice_region_variant', models.BoolField(null=True, blank=True)),
        ])),
        ('utrannotator', NamedTupleField([
            ('existingInframeOorfs', models.Int32Field(null=True, blank=True)),
            ('existingOutofframeOorfs', models.Int32Field(null=True, blank=True)),
            ('existingUorfs', models.Int32Field(null=True, blank=True)),
            ('fiveutrAnnotation', NamedTupleField([
                ('AltStop', models.StringField(null=True, blank=True)),
                ('AltStopDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('CapDistanceToStart', models.Int32Field(null=True, blank=True)),
                ('DistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('DistanceToStop', models.Int32Field(null=True, blank=True)),
                ('Evidence', models.BoolField(null=True, blank=True)),
                ('FrameWithCDS', models.StringField(null=True, blank=True)),
                ('KozakContext', models.StringField(null=True, blank=True)),
                ('KozakStrength', models.StringField(null=True, blank=True)),
                ('StartDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('alt_type', models.StringField(null=True, blank=True)),
                ('alt_type_length', models.Int32Field(null=True, blank=True)),
                ('newSTOPDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('ref_StartDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('ref_type', models.StringField(null=True, blank=True)),
                ('ref_type_length', models.Int32Field(null=True, blank=True)),
                ('type', models.StringField(null=True, blank=True)),
            ], null_if_empty=True)),
            ('fiveutrConsequence', models.StringField(null=True, blank=True)),
        ])),
        *BaseAnnotationsMitoSnvIndel.TRANSCRIPTS_FIELDS,
    ]), group_by_key='geneId')

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/transcripts'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/transcripts', primary_key='key', flatten_nested=0)

class BaseKeyLookup(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId')

    class Meta:
        abstract = True

class KeyLookupGRCh37SnvIndel(BaseKeyLookup):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/key_lookup', primary_key='variant_id', flatten_nested=0)

class KeyLookupSnvIndel(BaseKeyLookup):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupMito(BaseKeyLookup):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/MITO/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/MITO/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupSv(BaseKeyLookup):
    key = OneToOneField('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SV/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SV/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupGcnv(BaseKeyLookup):
    key = OneToOneField('AnnotationsGcnv', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/GCNV/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/GCNV/key_lookup', primary_key='variant_id', flatten_nested=0)


class BaseProjectGtStats(models.ClickhouseModel):
    project_guid = models.StringField(low_cardinality=True)
    ref_samples = models.UInt32Field()
    het_samples = models.UInt32Field()
    hom_samples = models.UInt32Field()

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by=('project_guid', 'key'),
            partition_by='project_guid',
            index_granularity=8192,
        )

class BaseProjectGtStatsMitoSnvIndel(BaseProjectGtStats):
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by=('project_guid', 'key', 'sample_type'),
            partition_by='project_guid',
            index_granularity=8192,
        )

class ProjectGtStatsGRCh37SnvIndel(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh37/SNV_INDEL/project_gt_stats'

class ProjectGtStatsSnvIndel(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh38/SNV_INDEL/project_gt_stats'

class ProjectGtStatsMito(BaseProjectGtStatsMitoSnvIndel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStatsMitoSnvIndel.Meta):
        db_table = 'GRCh38/MITO/project_gt_stats'

class ProjectGtStatsSv(BaseProjectGtStats):
    key = OneToOneField('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseProjectGtStats.Meta):
        db_table = 'GRCh38/SV/project_gt_stats'


class BaseGtStats(models.ClickhouseModel):
    ac_wes = models.UInt32Field()
    ac_wgs = models.UInt32Field()
    hom_wes = models.UInt32Field()
    hom_wgs = models.UInt32Field()

    class Meta:
        abstract = True
        engine = models.SummingMergeTree(
            order_by='key',
            index_granularity=8192,
        )

class GtStatsGRCh37SnvIndel(BaseGtStats):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh37/SNV_INDEL/gt_stats'

class GtStatsSnvIndel(BaseGtStats):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/SNV_INDEL/gt_stats'

class GtStatsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac_het_wes = models.UInt32Field()
    ac_het_wgs = models.UInt32Field()
    ac_hom_wes = models.UInt32Field()
    ac_hom_wgs = models.UInt32Field()

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/MITO/gt_stats'

class GtStatsSv(models.ClickhouseModel):
    key = OneToOneField('AnnotationsSv', db_column='key', primary_key=True, on_delete=CASCADE)
    ac_wgs = models.UInt32Field()
    hom_wgs = models.UInt32Field()

    class Meta(BaseGtStats.Meta):
        db_table = 'GRCh38/SV/gt_stats'


ENTRY_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: EntriesGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: EntriesSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: EntriesMito,
    },
}
ANNOTATIONS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: AnnotationsGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: AnnotationsSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: AnnotationsMito,
    },
}
TRANSCRIPTS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: TranscriptsGRCh37SnvIndel,
    GENOME_VERSION_GRCh38: TranscriptsSnvIndel,
}
