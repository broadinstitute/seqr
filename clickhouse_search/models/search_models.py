from clickhouse_backend import models
from django.db.models import ForeignKey, OneToOneField, Func, CASCADE

from clickhouse_search.backend.engines import CollapsingMergeTree, EmbeddedRocksDB
from clickhouse_search.backend.fields import Enum8Field, NestedField, UInt32FieldDeltaCodecField, UInt64FieldDeltaCodecField, NamedTupleField, MaterializedUInt8Field
from clickhouse_search.backend.functions import ArrayDistinct, ArrayFlatten, ArrayMin, ArrayMax
from clickhouse_search.backend.table_models import Dictionary, FixtureLoadableClickhouseModel
from clickhouse_search.managers import EntriesManager, SvEntriesManager, SvVariantsQuerySet, VariantsQuerySet, \
    VariantDetailsQuerySet
from clickhouse_search.models.reference_data_models import GnomadNonCodingConstraintDict, BaseSpliceAi, \
    ScreenDict
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample
from seqr.utils.xpos_utils import CHROMOSOME_CHOICES
from settings import CLICKHOUSE_IN_MEMORY_DIR, CLICKHOUSE_DATA_DIR


class Projection(Func):

    def __init__(self, name, select='*', order_by=None):
        self.name = name
        self.select = select
        self.order_by = order_by


class BaseVariants(FixtureLoadableClickhouseModel):
    CONSEQUENCE_TERMS = [(1, 'transcript_ablation'), (2, 'splice_acceptor_variant'), (3, 'splice_donor_variant'), (4, 'stop_gained'), (5, 'frameshift_variant'), (6, 'stop_lost'), (7, 'start_lost'), (8, 'inframe_insertion'), (9, 'inframe_deletion'), (10, 'missense_variant'), (11, 'protein_altering_variant'), (12, 'splice_donor_5th_base_variant'), (13, 'splice_region_variant'), (14, 'splice_donor_region_variant'), (15, 'splice_polypyrimidine_tract_variant'), (16, 'incomplete_terminal_codon_variant'), (17, 'start_retained_variant'), (18, 'stop_retained_variant'), (19, 'synonymous_variant'), (20, 'coding_sequence_variant'), (21, 'mature_miRNA_variant'), (22, '5_prime_UTR_variant'), (23, '3_prime_UTR_variant'), (24, 'non_coding_transcript_exon_variant'), (25, 'intron_variant'), (26, 'NMD_transcript_variant'), (27, 'non_coding_transcript_variant'), (28, 'coding_transcript_variant'), (29, 'upstream_gene_variant'), (30, 'downstream_gene_variant'), (31, 'intergenic_variant'), (32, 'sequence_variant')]
    ANNOTATION_CONSTANTS = {
        'genomeVersion': GENOME_VERSION_GRCh38,
        'liftedOverGenomeVersion': GENOME_VERSION_GRCh37,
    }
    SCREEN_DICT = None
    VARIANT_PREDICTIONS = []

    key = UInt32FieldDeltaCodecField(primary_key=True)

    objects = VariantsQuerySet.as_manager()

    class Meta:
        abstract = True

class BaseVariantsSvGcnv(BaseVariants):
    SV_TYPE_FILTER_PREFIX = ''
    GENOTYPE_OVERRIDE_FIELDS = {}
    SV_CONSEQUENCE_RANKS = [(1,'LOF'), (2,'INTRAGENIC_EXON_DUP'), (3,'PARTIAL_EXON_DUP'), (4,'COPY_GAIN'), (5,'DUP_PARTIAL'), (6,'MSV_EXON_OVERLAP'), (7,'INV_SPAN'), (8,'UTR'), (9,'PROMOTER'), (10,'TSS_DUP'), (11,'BREAKEND_EXONIC'), (12,'INTRONIC'), (13,'NEAREST_TSS'),]
    SV_TYPES =  [(1,'gCNV_DEL'), (2,'gCNV_DUP'), (3,'BND'), (4,'CPX'), (5,'CTX'), (6,'DEL'), (7,'DUP'), (8,'INS'), (9,'INV'), (10,'CNV')]
    PREDICTION_FIELDS = [
        ('strvctvre', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    SORTED_GENE_CONSQUENCES_FIELDS = [
        ('geneId', models.StringField(null=True, blank=True)),
        ('majorConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=SV_CONSEQUENCE_RANKS)),
    ]

    xpos = models.UInt64Field()
    pos = models.UInt32Field()
    variant_id = models.StringField(db_column='variantId')
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)
    chrom = Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES)
    end = models.UInt32Field()
    rg37_locus_end = NamedTupleField([
        ('contig', models.Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES, null=True, blank=True)),
        ('position', models.UInt32Field(null=True, blank=True)),
    ], db_column='rg37LocusEnd', null_if_empty=True)
    lifted_over_chrom = Enum8Field(db_column='liftedOverChrom', return_int=False, null=True, blank=True, choices=CHROMOSOME_CHOICES)
    sv_type = Enum8Field(db_column='svType', return_int=False, choices=SV_TYPES)
    predictions = NamedTupleField(PREDICTION_FIELDS)
    sorted_gene_consequences = NestedField(SORTED_GENE_CONSQUENCES_FIELDS, db_column='sortedGeneConsequences', group_by_key='geneId')

    objects = SvVariantsQuerySet.as_manager()

    class Meta:
        abstract = True

class BaseVariantsGRCh37SnvIndel(BaseVariants):
    SORTED_TRANSCRIPT_CONSQUENCES_FIELDS = [
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseVariants.CONSEQUENCE_TERMS))),
        ('geneId', models.StringField(null=True, blank=True))
    ]
    ANNOTATION_CONSTANTS = {
        'genomeVersion': GENOME_VERSION_GRCh37,
        'liftedOverGenomeVersion': GENOME_VERSION_GRCh38,
    }

    sorted_transcript_consequences = NestedField(SORTED_TRANSCRIPT_CONSQUENCES_FIELDS, db_column='sortedTranscriptConsequences')

    class Meta:
        abstract = True

class VariantsGRCh37SnvIndel(BaseVariantsGRCh37SnvIndel):

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/variants_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh37/SNV_INDEL/variants', primary_key='key', flatten_nested=0)

class VariantsDiskGRCh37SnvIndel(BaseVariantsGRCh37SnvIndel):

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/variants_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/variants', primary_key='key', flatten_nested=0)

class BaseVariantsSnvIndel(BaseVariantsGRCh37SnvIndel):
    SORTED_TRANSCRIPT_CONSQUENCES_FIELDS = sorted([
        ('alphamissensePathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ('extendedIntronicSpliceRegionVariant', models.BoolField(null=True, blank=True)),
        ('fiveutrConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(1, '5_prime_UTR_premature_start_codon_gain_variant'), (2, '5_prime_UTR_premature_start_codon_loss_variant'), (3, '5_prime_UTR_stop_codon_gain_variant'), (4, '5_prime_UTR_stop_codon_loss_variant'), (5, '5_prime_UTR_uORF_frameshift_variant')])),
        ('isManeSelect', models.BoolField(null=True, blank=True)),
        *BaseVariantsGRCh37SnvIndel.SORTED_TRANSCRIPT_CONSQUENCES_FIELDS,
    ])
    SORTED_MOTIF_FEATURE_CONSEQUENCES_FIELDS = sorted([
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'TFBS_ablation'), (1, 'TFBS_amplification'), (2, 'TF_binding_site_variant'), (3, 'TFBS_fusion'), (4, 'TFBS_translocation')]))),
    ])
    SORTED_REGULATORY_FEATURE_CONSEQUENCES_FIELDS = sorted([
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'regulatory_region_ablation'), (1, 'regulatory_region_amplification'), (2, 'regulatory_region_variant'), (3, 'regulatory_region_fusion')]))),
    ])
    ANNOTATION_CONSTANTS = BaseVariants.ANNOTATION_CONSTANTS

    sorted_transcript_consequences = NestedField(SORTED_TRANSCRIPT_CONSQUENCES_FIELDS, db_column='sortedTranscriptConsequences')
    sorted_motif_feature_consequences = NestedField(SORTED_MOTIF_FEATURE_CONSEQUENCES_FIELDS, db_column='sortedMotifFeatureConsequences', null_when_empty=True)
    sorted_regulatory_feature_consequences = NestedField(SORTED_REGULATORY_FEATURE_CONSEQUENCES_FIELDS, db_column='sortedRegulatoryFeatureConsequences', null_when_empty=True)

    class Meta:
        abstract = True

class VariantsSnvIndel(BaseVariantsSnvIndel):
    SCREEN_DICT = ScreenDict

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/variants_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SNV_INDEL/variants', primary_key='key', flatten_nested=0)

class VariantsDiskSnvIndel(BaseVariantsSnvIndel):

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/variants_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/variants', primary_key='key', flatten_nested=0)

class BaseVariantsMito(BaseVariants):
    TRANSCRIPTS_FIELDS = [
        ('aminoAcids', models.StringField(null=True, blank=True)),
        ('biotype', models.StringField(null=True, blank=True)),
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('codons', models.StringField(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseVariants.CONSEQUENCE_TERMS))),
        ('geneId', models.StringField(null=True, blank=True)),
        ('hgvsc', models.StringField(null=True, blank=True)),
        ('hgvsp', models.StringField(null=True, blank=True)),
        ('loftee', NamedTupleField([
            ('isLofNagnag', models.BoolField(null=True, blank=True)),
            ('lofFilters', models.ArrayField(models.StringField(null=True, blank=True))),
        ], null_empty_arrays=True)),
        ('majorConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=BaseVariants.CONSEQUENCE_TERMS)),
        ('transcriptId', models.StringField()),
        ('transcriptRank', models.UInt8Field()),
    ]
    MITOTIP_PATHOGENICITIES = [
        (0, 'likely_pathogenic'),
        (1, 'possibly_pathogenic'),
        (2, 'possibly_benign'),
        (3, 'likely_benign'),
    ]
    ANNOTATION_CONSTANTS = {
        'chrom': 'M',
        'liftedOverChrom': 'MT',
        **BaseVariants.ANNOTATION_CONSTANTS,
    }
    VARIANT_PREDICTIONS = ['haplogroupDefining', 'mitotip']

    variant_id = models.StringField(db_column='variantId')
    rsid = models.StringField(null=True, blank=True)
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)
    sorted_transcript_consequences = NestedField(TRANSCRIPTS_FIELDS, db_column='sortedTranscriptConsequences', group_by_key='geneId')
    haplogroup_defining = models.BoolField(null=True, blank=True, db_column='haplogroupDefining')
    mitotip = models.Enum8Field(null=True, blank=True, return_int=False, choices=MITOTIP_PATHOGENICITIES)
    common_low_heteroplasmy = models.BoolField(db_column='commonLowHeteroplasmy', null=True, blank=True)
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)

    class Meta:
        abstract = True

class VariantsMito(BaseVariantsMito):

    class Meta:
        db_table = 'GRCh38/MITO/variants_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/MITO/variants', primary_key='key', flatten_nested=0)

class VariantsDiskMito(BaseVariantsMito):

    class Meta:
        db_table = 'GRCh38/MITO/variants_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/MITO/variants', primary_key='key', flatten_nested=0)

class BaseVariantsSv(BaseVariantsSvGcnv):
    POPULATION_FIELDS = [
        ('gnomad_svs', NamedTupleField([
            ('af', models.DecimalField(max_digits=9, decimal_places=8)),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
            ('id', models.StringField()),
        ])),
    ]
    SV_TYPE_DETAILS = [(1, 'INS_iDEL'),(2, 'INVdel'),(3, 'INVdup'),(4, 'ME'),(5, 'ME:ALU'),(6, 'ME:LINE1'),(7, 'ME:SVA'),(8, 'dDUP'),(9, 'dDUP_iDEL'),(10, 'delINV'),(11, 'delINVdel'),(12, 'delINVdup'),(13, 'dupINV'),(14, 'dupINVdel'),(15, 'dupINVdup')]

    algorithms = models.StringField(low_cardinality=True)
    bothsides_support = models.BoolField(db_column='bothsidesSupport')
    cpx_intervals = NestedField([
        ('chrom', models.Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES)),
        ('start', models.UInt32Field()),
        ('end', models.UInt32Field()),
        ('type', models.Enum8Field(return_int=False, choices=BaseVariantsSvGcnv.SV_TYPES)),
    ], db_column='cpxIntervals', null_when_empty=True)
    end_chrom = models.Enum8Field(db_column='endChrom', return_int=False, choices=CHROMOSOME_CHOICES, null=True, blank=True)
    sv_source_detail = NamedTupleField(
        [('chrom', models.Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES, null=True, blank=True))],
        db_column='svSourceDetail',
        null_if_empty=True
    )
    sv_type_detail = models.Enum8Field(db_column='svTypeDetail', return_int=False, choices=SV_TYPE_DETAILS, null=True, blank=True)
    populations = NamedTupleField(POPULATION_FIELDS)

    class Meta:
        abstract = True

class VariantsSv(BaseVariantsSv):

    class Meta:
        db_table = 'GRCh38/SV/variants_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SV/variants', primary_key='key', flatten_nested=0)

class VariantsDiskSv(BaseVariantsSv):

    class Meta:
        db_table = 'GRCh38/SV/variants_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SV/variants', primary_key='key', flatten_nested=0)

class BaseVariantsGcnv(BaseVariantsSvGcnv):
    POPULATION_FIELDS = [
        ('sv_callset', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=8)),
            ('an', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
    ]
    SV_TYPE_FILTER_PREFIX = 'gCNV_'
    GENOTYPE_OVERRIDE_FIELDS = {
        'pos': ('start', ArrayMin),
        'end': ('end', ArrayMax),
        'numExon': ('numExon', ArrayMax),
        'geneIds': ('geneIds', lambda value, **kwargs: ArrayDistinct(ArrayFlatten(value), **kwargs)),
    }

    num_exon = models.UInt16Field(db_column='numExon')
    populations = NamedTupleField(POPULATION_FIELDS)

    class Meta:
        abstract = True

class VariantsGcnv(BaseVariantsGcnv):

    class Meta:
        db_table = 'GRCh38/GCNV/variants_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/GCNV/variants', primary_key='key', flatten_nested=0)

class VariantsDiskGcnv(BaseVariantsGcnv):

    class Meta:
        db_table = 'GRCh38/GCNV/variants_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/GCNV/variants', primary_key='key', flatten_nested=0)

class BaseEntries(FixtureLoadableClickhouseModel):

    project_guid = models.StringField(low_cardinality=True)
    family_guid = models.StringField()
    xpos = UInt64FieldDeltaCodecField()
    filters = models.ArrayField(models.StringField(low_cardinality=True))
    sign = models.Int8Field()

    objects = EntriesManager.as_manager()

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
    PREDICTIONS = {
        'splice_ai': {
            'consequence_id': ('splice_ai_consequence', models.Enum8Field(choices=[(csq, csq_id) for csq_id, csq in BaseSpliceAi.CONSEQUENCE_CHOICES])),
        },
        'dbnsfp': {},
        'eigen': {},
    }
    RANGE_PREDICTIONS = {}
    POPULATIONS = ['gnomad_exomes', 'gnomad_genomes', 'topmed']

    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    is_gnomad_gt_5_percent = models.BoolField()
    is_annotated_in_any_gene = models.BoolField()
    geneId_ids = models.ArrayField(models.UInt32Field())
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    class Meta:
        abstract = True
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'sample_type', 'is_gnomad_gt_5_percent', 'is_annotated_in_any_gene', 'key'),
            partition_by='project_guid',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )
        projection = Projection('xpos_projection', order_by='is_gnomad_gt_5_percent, is_annotated_in_any_gene, xpos')

class EntriesGRCh37SnvIndel(BaseEntriesSnvIndel):

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('VariantsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta(BaseEntriesSnvIndel.Meta):
        db_table = 'GRCh37/SNV_INDEL/entries'

class EntriesSnvIndel(BaseEntriesSnvIndel):
    PREDICTIONS = {
        **BaseEntriesSnvIndel.PREDICTIONS,
        'absplice': {},
        'pext': {},
        'promoter_ai': {},
    }
    RANGE_PREDICTIONS = {
        'gnomad_noncoding': GnomadNonCodingConstraintDict,
    }

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('VariantsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    partition_id = MaterializedUInt8Field(
        expression="farmHash64(family_guid) % n_partitions",
    )
    n_partitions = MaterializedUInt8Field(
        expression="dictGetOrDefault('GRCh38/SNV_INDEL/project_partitions_dict', 'n_partitions', project_guid, 1)",
    )

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/entries'
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'sample_type', 'is_gnomad_gt_5_percent', 'is_annotated_in_any_gene', 'key'),
            partition_by='project_guid, partition_id',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )

    def _save_table(
        self,
        *args, **kwargs,
    ):
        # Exclude derived fields from fixture insert.
        # Note that just deleting the attributes is insufficient due
        # to fields mismatch on db refresh.
        self._meta.local_concrete_fields = [
            f for f in self._meta.local_concrete_fields
            if f.name not in ['partition_id', 'n_partitions']
        ]
        return super()._save_table(
            *args, **kwargs,
        )

class EntriesMito(BaseEntries):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('dp', models.UInt16Field(null=True, blank=True)),
        ('hl', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mitoCn', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('contamination', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    PREDICTIONS = {
        'apogee': {},
        'dbnsfp': {},
        'hmtvar': {},
        'mlc': {},
        'pext': {},
    }
    RANGE_PREDICTIONS = {}
    POPULATIONS = ['gnomad_mito', 'gnomad_mito_heteroplasmy', 'helix', 'helix_heteroplasmy']

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('VariantsMito', db_column='key', primary_key=True, on_delete=CASCADE)
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
    SAMPLE_TYPE = Sample.SAMPLE_TYPE_WGS
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('cn', models.UInt8Field(null=True, blank=True)),
        ('gq', models.UInt8Field(null=True, blank=True)),
        ('newCall', models.BoolField(null=True, blank=True)),
        ('prevCall', models.BoolField(null=True, blank=True)),
        ('prevNumAlt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
    ]

    objects = SvEntriesManager.as_manager()

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('VariantsSv', db_column='key', primary_key=True, on_delete=CASCADE)
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))
    geneId_ids = models.ArrayField(models.UInt32Field())

    class Meta(BaseEntries.Meta):
        db_table = 'GRCh38/SV/entries'

class EntriesGcnv(BaseEntries):
    SAMPLE_TYPE = Sample.SAMPLE_TYPE_WES
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
    key = ForeignKey('VariantsGcnv', db_column='key', primary_key=True, on_delete=CASCADE)
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))

    objects = SvEntriesManager.as_manager()

    class Meta(BaseEntries.Meta):
        db_table = 'GRCh38/GCNV/entries'

class VariantDetailsGRCh37SnvIndel(models.ClickhouseModel):
    ANNOTATION_CONSTANTS = VariantsGRCh37SnvIndel.ANNOTATION_CONSTANTS

    key = OneToOneField('VariantsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    variant_id = models.StringField(db_column='variantId')
    lifted_over_chrom = Enum8Field(db_column='liftedOverChrom', return_int=False, null=True, blank=True, choices=CHROMOSOME_CHOICES)
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)
    rsid = models.StringField(null=True, blank=True)
    caid = models.StringField(db_column='CAID', null=True, blank=True)
    transcripts = NestedField(BaseVariantsMito.TRANSCRIPTS_FIELDS, group_by_key='geneId')

    objects = VariantDetailsQuerySet.as_manager()

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/variants/details'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/variants_details', primary_key='key', flatten_nested=0)

class VariantDetailsSnvIndel(models.ClickhouseModel):
    TRANSCRIPTS_FIELDS = sorted([
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
        *BaseVariantsMito.TRANSCRIPTS_FIELDS,
    ])
    SORTED_MOTIF_FEATURE_CONSEQUENCES_FIELDS = sorted([
        ('motifFeatureId', models.StringField(null=True, blank=True)),
        *BaseVariantsSnvIndel.SORTED_MOTIF_FEATURE_CONSEQUENCES_FIELDS,
    ])
    SORTED_REGULATORY_FEATURE_CONSEQUENCES_FIELDS = sorted([
        ('biotype', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'enhancer'), (1, 'promoter'), (2, 'CTCF_binding_site'), (3, 'TF_binding_site'), (4, 'open_chromatin_region')])),
        ('regulatoryFeatureId', models.StringField(null=True, blank=True)),
        *BaseVariantsSnvIndel.SORTED_REGULATORY_FEATURE_CONSEQUENCES_FIELDS,
    ])
    ANNOTATION_CONSTANTS = VariantsSnvIndel.ANNOTATION_CONSTANTS
    SCREEN_DICT = VariantsSnvIndel.SCREEN_DICT

    key = OneToOneField('VariantsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    variant_id = models.StringField(db_column='variantId')
    lifted_over_chrom = Enum8Field(db_column='liftedOverChrom', return_int=False, null=True, blank=True, choices=CHROMOSOME_CHOICES)
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)
    rsid = models.StringField(null=True, blank=True)
    caid = models.StringField(db_column='CAID', null=True, blank=True)
    transcripts = NestedField(TRANSCRIPTS_FIELDS, group_by_key='geneId')
    sorted_motif_feature_consequences = NestedField(SORTED_MOTIF_FEATURE_CONSEQUENCES_FIELDS, db_column='sortedMotifFeatureConsequences', null_when_empty=True)
    sorted_regulatory_feature_consequences = NestedField(SORTED_REGULATORY_FEATURE_CONSEQUENCES_FIELDS, db_column='sortedRegulatoryFeatureConsequences', null_when_empty=True)

    objects = VariantDetailsQuerySet.as_manager()

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/variants/details'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/variants_details', primary_key='key', flatten_nested=0)

class BaseKeyLookup(FixtureLoadableClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        abstract = True

class KeyLookupGRCh37SnvIndel(BaseKeyLookup):
    key = OneToOneField('VariantsGRCh37SnvIndel', db_column='key', on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh37/SNV_INDEL/key_lookup', primary_key='variant_id', flatten_nested=0)

class KeyLookupSnvIndel(BaseKeyLookup):
    key = OneToOneField('VariantsSnvIndel', db_column='key', on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupMito(BaseKeyLookup):
    key = OneToOneField('VariantsMito', db_column='key', on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/MITO/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/MITO/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupSv(BaseKeyLookup):
    key = OneToOneField('VariantsSv', db_column='key', on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SV/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SV/key_lookup', primary_key='variant_id', flatten_nested=0)


class KeyLookupGcnv(BaseKeyLookup):
    key = OneToOneField('VariantsGcnv', db_column='key', on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/GCNV/key_lookup'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/GCNV/key_lookup', primary_key='variant_id', flatten_nested=0)


class ProjectPartitionsSnvIndel(FixtureLoadableClickhouseModel):
    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    project_guid = models.StringField(primary_key=True)
    n_partitions = models.UInt8Field()
    class Meta:
        db_table = 'GRCh38/SNV_INDEL/project_partitions'
        engine = models.MergeTree(
            primary_key='project_guid',
            order_by='project_guid',
        )

class ProjectPartitionsDict(Dictionary):
    project_guid = models.StringField(primary_key=True)
    n_partitions = models.UInt8Field()

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/project_partitions_dict'
        engine = models.MergeTree(primary_key='project_guid')
        source_table = 'ProjectPartitionsSnvIndel'
        lifetime_max = 300 # refresh every 5 minutes
        layout = 'HASHED()' # hashed layout supports string keys


ENTRY_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: EntriesGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: EntriesSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: EntriesMito,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}': EntriesSv,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}': EntriesGcnv,
    },
}
VARIANTS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: {Sample.DATASET_TYPE_VARIANT_CALLS: VariantsGRCh37SnvIndel},
    GENOME_VERSION_GRCh38: {
        Sample.DATASET_TYPE_VARIANT_CALLS: VariantsSnvIndel,
        Sample.DATASET_TYPE_MITO_CALLS: VariantsMito,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}': VariantsSv,
        f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}': VariantsGcnv,
    },
}
VARIANT_DETAILS_CLASS_MAP = {
    GENOME_VERSION_GRCh37: VariantDetailsGRCh37SnvIndel,
    GENOME_VERSION_GRCh38: VariantDetailsSnvIndel,
}
