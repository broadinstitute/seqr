from django.db.migrations import state
from django.db.models import options, ForeignKey, Func, Value, CASCADE

from clickhouse_backend import models

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


def _no_validate(value, name):
    return value


class Projection(Func):

    def __init__(self, name, select='*', order_by=None):
        self.name = name
        self.select = select
        self.order_by = order_by


class CollapsingMergeTree(models.CollapsingMergeTree):
    setting_types = {
        **models.CollapsingMergeTree.setting_types,
        _no_validate: ['deduplicate_merge_projection_mode']
    }


class EmbeddedRocksDB(models.BaseMergeTree):
    arity = 2

    def __init__(self, ttl, rocksdb_dir, **settings):
        super().__init__(ttl, Value(rocksdb_dir), **settings)


class NestedField(models.TupleField):

    def get_internal_type(self):
        return "NestedField"

    @property
    def description(self):
        return super().description().replace('Tuple', 'Nested', 1)

    def db_type(self, connection):
        return super().db_type(connection).replace('Tuple', 'Nested', 1)

    def cast_db_type(self, connection):
        return super().cast_db_type(connection).replace('Tuple', 'Nested', 1)


class EntriesSnvIndel(models.ClickhouseModel):
    project_guid = models.StringField()
    family_guid = models.StringField()
    sample_ids = models.ArrayField(models.StringField())
    key = ForeignKey('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    xpos = models.UInt64Field()
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    is_gnomad_gt_5_percent = models.BoolField()
    gt = models.ArrayField(models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')]), db_column='GT')
    gq = models.ArrayField(models.Int32Field(null=True, blank=True), db_column='GQ')
    ab = models.ArrayField(models.Float32Field(null=True, blank=True), db_column='AB')
    dp = models.ArrayField(models.Int32Field(null=True, blank=True), db_column='DP')
    sign = models.Int8Field()

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/entries'
        ordering = ['project_guid', 'family_guid', 'is_gnomad_gt_5_percent', 'key']
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'is_gnomad_gt_5_percent', 'key'),
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )
        projection = Projection('xpos_projection', order_by='xpos')


class AnnotationsSnvIndel(models.ClickhouseModel):
    key = models.UInt32Field(primary_key=True)
    xpos = models.UInt64Field()
    chrom = models.StringField(low_cardinality=True)
    pos = models.UInt32Field()
    ref = models.StringField()
    alt = models.StringField()
    variant_id = models.StringField(db_column='variantId')
    rsid = models.StringField(null=True, blank=True)
    caid = models.StringField(db_column='CAID', null=True, blank=True)
    lifted_over_chrom = models.StringField(db_column='liftedOverChrom', low_cardinality=True, null=True, blank=True)
    lifted_over_pos = models.StringField(db_column='liftedOverPos', null=True, blank=True)
    hgmd = models.TupleField([
        ('accession', models.StringField(null=True, blank=True)),
        ('class_', models.Enum8Field(null=True, blank=True, choices=[(0, 'DM'), (1, 'DM?'), (2, 'DP'), (3, 'DFP'), (4, 'FP'), (5, 'R')])),
    ])
    screen_region_type = models.Enum8Field(db_column='screenRegionType', null=True, blank=True, choices=[(0, 'CTCF-bound'), (1, 'CTCF-only'), (2, 'DNase-H3K4me3'), (3, 'PLS'), (4, 'dELS'), (5, 'pELS'), (6, 'DNase-only'), (7, 'low-DNase')])
    predictions = models.TupleField([
        ('cadd', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('eigen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('fathmm', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('gnomad_noncoding', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mpc', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_pred', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_taster', models.Enum8Field(null=True, blank=True, choices=[(0, 'D'), (1, 'A'), (2, 'N'), (3, 'P')])),
        ('polyphen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('primate_ai', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('revel', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('sift', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('splice_ai', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('splice_ai_consequence', models.Enum8Field(null=True, blank=True, choices=[(0, 'Acceptor gain'), (1, 'Acceptor loss'), (2, 'Donor gain'), (3, 'Donor loss'), (4, 'No consequence')])),
        ('vest', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ])
    populations = models.TupleField([
        ('exac', models.TupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_exomes', models.TupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_genomes', models.TupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('topmed', models.TupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
    ])
    sorted_transcript_consequences = NestedField([
        ('alphamissense', models.TupleField([
            ('pathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ])),
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, choices=[(1, 'transcript_ablation'), (2, 'splice_acceptor_variant'), (3, 'splice_donor_variant'), (4, 'stop_gained'), (5, 'frameshift_variant'), (6, 'stop_lost'), (7, 'start_lost'), (8, 'inframe_insertion'), (9, 'inframe_deletion'), (10, 'missense_variant'), (11, 'protein_altering_variant'), (12, 'splice_donor_5th_base_variant'), (13, 'splice_region_variant'), (14, 'splice_donor_region_variant'), (15, 'splice_polypyrimidine_tract_variant'), (16, 'incomplete_terminal_codon_variant'), (17, 'start_retained_variant'), (18, 'stop_retained_variant'), (19, 'synonymous_variant'), (20, 'coding_sequence_variant'), (21, 'mature_miRNA_variant'), (22, '5_prime_UTR_variant'), (23, '3_prime_UTR_variant'), (24, 'non_coding_transcript_exon_variant'), (25, 'intron_variant'), (26, 'NMD_transcript_variant'), (27, 'non_coding_transcript_variant'), (28, 'coding_transcript_variant'), (29, 'upstream_gene_variant'), (30, 'downstream_gene_variant'), (31, 'intergenic_variant'), (32, 'sequence_variant')]))),
        ('geneId', models.StringField(null=True, blank=True)),
        ('spliceregion', models.TupleField([
            ('extended_intronic_splice_region_variant', models.BoolField(null=True, blank=True)),
        ])),
        ('utrannotator', models.TupleField([
            ('fiveutrConsequence', models.Enum8Field(null=True, blank=True, choices=[(1, '5_prime_UTR_premature_start_codon_gain_variant'), (2, '5_prime_UTR_premature_start_codon_loss_variant'), (3, '5_prime_UTR_stop_codon_gain_variant'), (4, '5_prime_UTR_stop_codon_loss_variant'), (5, '5_prime_UTR_uORF_frameshift_variant')])),
        ])),
    ], db_column='sortedTranscriptConsequences')
    sorted_motif_feature_consequences = NestedField([
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, choices=[(0, 'TFBS_ablation'), (1, 'TFBS_amplification'), (2, 'TF_binding_site_variant'), (3, 'TFBS_fusion'), (4, 'TFBS_translocation')]))),
        ('motifFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedMotifFeatureConsequences')
    sorted_regulatory_feature_consequences = NestedField([
        ('biotype', models.Enum8Field(null=True, blank=True, choices=[(0, 'enhancer'), (1, 'promoter'), (2, 'CTCF_binding_site'), (3, 'TF_binding_site'), (4, 'open_chromatin_region')])),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, choices=[(0, 'regulatory_region_ablation'), (1, 'regulatory_region_amplification'), (2, 'regulatory_region_variant'), (3, 'regulatory_region_fusion')]))),
        ('regulatoryFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedRegulatoryFeatureConsequences')

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/annotations'
        # TODO add configuration for in-memory-dir, remove trailing suffix? move into engine class def?
        engine = EmbeddedRocksDB(0, f'/in-memory-dir/{db_table}3', primary_key='key')


# class Grch38SnvIndelClinvar(models.ClickhouseModel):
#     key = models.UInt32Field()
#     alleleid = models.UInt32Field(db_column='alleleId', null=True, blank=True)  # Field name made lowercase.
#     conflictingpathogenicities = models.NestedField(db_column='conflictingPathogenicities')  # Field name made lowercase.
#     goldstars = models.UInt8Field(db_column='goldStars', null=True, blank=True)  # Field name made lowercase.
#     submitters = models.ArrayField(models.StringField())
#     conditions = models.ArrayField(models.StringField(null=True, blank=True))
#     assertions = models.ArrayField(models.Enum8Field(choices=[(0, 'Affects'), (1, 'association'), (2, 'association_not_found'), (3, 'confers_sensitivity'), (4, 'drug_response'), (5, 'low_penetrance'), (6, 'not_provided'), (7, 'other'), (8, 'protective'), (9, 'risk_factor'), (10, 'no_classification_for_the_single_variant'), (11, 'no_classifications_from_unflagged_records')]))
#     pathogenicity = models.Enum8Field(choices=[(0, 'Pathogenic'), (1, 'Pathogenic/Likely_pathogenic'), (2, 'Pathogenic/Likely_pathogenic/Established_risk_allele'), (3, 'Pathogenic/Likely_pathogenic/Likely_risk_allele'), (4, 'Pathogenic/Likely_risk_allele'), (5, 'Likely_pathogenic'), (6, 'Likely_pathogenic/Likely_risk_allele'), (7, 'Established_risk_allele'), (8, 'Likely_risk_allele'), (9, 'Conflicting_classifications_of_pathogenicity'), (10, 'Uncertain_risk_allele'), (11, 'Uncertain_significance/Uncertain_risk_allele'), (12, 'Uncertain_significance'), (13, 'No_pathogenic_assertion'), (14, 'Likely_benign'), (15, 'Benign/Likely_benign'), (16, 'Benign')])
#
#     class Meta:
#         db_table = 'GRCh38/SNV_INDEL/clinvar'
#
#
# class Grch38SnvIndelGtStats(models.ClickhouseModel):
#     project_guid = models.StringField()
#     key = models.UInt32Field()
#     ref_samples = models.AggregateFunctionField()
#     het_samples = models.AggregateFunctionField()
#     hom_samples = models.AggregateFunctionField()
#
#     class Meta:
#         db_table = 'GRCh38/SNV_INDEL/gt_stats'
