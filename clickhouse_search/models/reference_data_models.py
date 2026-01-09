from clickhouse_backend import models
from django.db.models import ForeignKey, OneToOneField, CASCADE, PROTECT

from clickhouse_search.backend.engines import Join
from clickhouse_search.backend.fields import Enum8Field, NestedField, UInt32FieldDeltaCodecField
from clickhouse_search.backend.table_models import FixtureLoadableClickhouseModel, RefreshableMaterializedView, RefreshableMaterializedViewMeta
from seqr.utils.xpos_utils import CHROMOSOME_CHOICES


def _all_variants_to_seqr_source_sql(reference_genome, dataset_type):
    return f'src INNER JOIN `{reference_genome}/{dataset_type}/key_lookup` dst on assumeNotNull(src.variantId) = dst.variantId'


class BaseClinvar(FixtureLoadableClickhouseModel):

    CLINVAR_ASSERTIONS = [
        'Affects',
        'association',
        'association_not_found',
        'confers_sensitivity',
        'drug_response',
        'low_penetrance',
        'not_provided',
        'other',
        'protective',
        'risk_factor',
        'no_classification_for_the_single_variant',
        'no_classifications_from_unflagged_records',
    ]
    CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY = 'Conflicting_classifications_of_pathogenicity'
    CLINVAR_DEFAULT_PATHOGENICITY = 'No_pathogenic_assertion'
    CLINVAR_PATHOGENICITIES = [
        'Pathogenic',
        'Pathogenic/Likely_pathogenic',
        'Pathogenic/Likely_pathogenic/Established_risk_allele',
        'Pathogenic/Likely_pathogenic/Likely_risk_allele',
        'Pathogenic/Likely_risk_allele',
        'Likely_pathogenic',
        'Likely_pathogenic/Likely_risk_allele',
        'Established_risk_allele',
        'Likely_risk_allele',
        CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY,
        'Uncertain_risk_allele',
        'Uncertain_significance/Uncertain_risk_allele',
        'Uncertain_significance',
        CLINVAR_DEFAULT_PATHOGENICITY,
        'Likely_benign',
        'Benign/Likely_benign',
        'Benign',
    ]

    ASSERTIONS_CHOICES = list(enumerate(CLINVAR_ASSERTIONS))
    PATHOGENICITY_CHOICES = list(enumerate(CLINVAR_PATHOGENICITIES))

    allele_id = models.UInt32Field(db_column='alleleId', null=True, blank=True)
    conflicting_pathogenicities = NestedField([
        ('pathogenicity', models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)),
        ('count', models.UInt16Field()),
    ], db_column='conflictingPathogenicities', null_when_empty=True)
    gold_stars = models.UInt8Field(db_column='goldStars', null=True, blank=True)
    submitters = models.ArrayField(models.StringField())
    conditions = models.ArrayField(models.StringField())
    assertions = models.ArrayField(models.Enum8Field(choices=ASSERTIONS_CHOICES, return_int=False))
    pathogenicity = models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)

    class Meta:
        abstract = True

class BaseClinvarAllVariants(BaseClinvar):
    version = models.DateField()
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        abstract = True
        engine = models.MergeTree(
            primary_key=('version', 'variant_id'),
            order_by=('version', 'variant_id'),
            partition_by='version',
        )

class ClinvarAllVariantsGRCh37SnvIndel(BaseClinvarAllVariants):
    class Meta(BaseClinvarAllVariants.Meta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar/all_variants'

class ClinvarAllVariantsSnvIndel(BaseClinvarAllVariants):
    class Meta(BaseClinvarAllVariants.Meta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar/all_variants'

class ClinvarAllVariantsMito(BaseClinvarAllVariants):
    class Meta(BaseClinvarAllVariants.Meta):
        db_table = 'GRCh38/MITO/reference_data/clinvar/all_variants'

class ClinvarSeqrVariantsGRCh37SnvIndel(BaseClinvar):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar/seqr_variants'
        engine = models.MergeTree(
            primary_key='key',
            order_by='key'
        )

class ClinvarSeqrVariantsSnvIndel(BaseClinvar):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants'
        engine = models.MergeTree(
            primary_key='key',
            order_by='key'
        )

class ClinvarSeqrVariantsMito(BaseClinvar):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh38/MITO/reference_data/clinvar/seqr_variants'
        engine = models.MergeTree(
            primary_key='key',
            order_by='key'
        )

class BaseClinvarJoin(BaseClinvar):

    class Meta:
        abstract = True
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)


class ClinvarGRCh37SnvIndel(BaseClinvarJoin):
    key = ForeignKey('EntriesGRCh37SnvIndel', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvarJoin.Meta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar'

class ClinvarSnvIndel(BaseClinvarJoin):
    key = ForeignKey('EntriesSnvIndel', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvarJoin.Meta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar'

class ClinvarMito(BaseClinvarJoin):
    key = ForeignKey('EntriesMito', db_column='key', related_name='clinvar_join', primary_key=True, on_delete=PROTECT)
    class Meta(BaseClinvarJoin.Meta):
        db_table = 'GRCh38/MITO/reference_data/clinvar'

class BaseClinvarMv(RefreshableMaterializedView):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    allele_id = models.UInt32Field(db_column='alleleId', null=True, blank=True)
    conflicting_pathogenicities = NestedField([
        ('pathogenicity', models.Enum8Field(choices=BaseClinvar.PATHOGENICITY_CHOICES, return_int=False)),
        ('count', models.UInt16Field()),
    ], db_column='conflictingPathogenicities', null_when_empty=True)
    gold_stars = models.UInt8Field(db_column='goldStars', null=True, blank=True)
    submitters = models.ArrayField(models.StringField())
    conditions = models.ArrayField(models.StringField())
    assertions = models.ArrayField(models.Enum8Field(choices=BaseClinvar.ASSERTIONS_CHOICES, return_int=False))
    pathogenicity = models.Enum8Field(choices=BaseClinvar.PATHOGENICITY_CHOICES, return_int=False)

    class Meta:
        abstract = True

class ClinvarMvMeta(RefreshableMaterializedViewMeta):
    column_selects = {
        'key': "DISTINCT ON (key)",
    }

class ClinvarMvGRCh37SnvIndel(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar/all_variants_to_seqr_variants_mv'
        to_table = 'ClinvarSeqrVariantsGRCh37SnvIndel'
        source_table = 'ClinvarAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class ClinvarMvSnvIndel(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar/all_variants_to_seqr_variants_mv'
        to_table = 'ClinvarSeqrVariantsSnvIndel'
        source_table = 'ClinvarAllVariantsSnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'SNV_INDEL')

class ClinvarMvMito(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh38/MITO/reference_data/clinvar/all_variants_to_seqr_variants_mv'
        to_table = 'ClinvarSeqrVariantsMito'
        source_table = 'ClinvarAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class ClinvarSearchMvGRCh37SnvIndel(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar/seqr_variants_to_search_mv'
        to_table = 'ClinvarGRCh37SnvIndel'
        source_table = 'ClinvarSeqrVariantsGRCh37SnvIndel'

class ClinvarSearchMvSnvIndel(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants_to_search_mv'
        to_table = 'ClinvarSnvIndel'
        source_table = 'ClinvarSeqrVariantsSnvIndel'

class ClinvarSearchMvMito(BaseClinvarMv):

    class Meta(ClinvarMvMeta):
        db_table = 'GRCh38/MITO/reference_data/clinvar/seqr_variants_to_search_mv'
        to_table = 'ClinvarMito'
        source_table = 'ClinvarSeqrVariantsMito'

class PextAllVariantsSnvIndel(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class PextAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/pext/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class PextSeqrVariantsSnvIndel(models.ClickhouseModel):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PextSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/pext/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadNonCodingConstraintAllVariantsSnvIndel(models.ClickhouseModel):
    chrom = Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES, primary_key=True)
    start = models.UInt32Field()
    end = models.UInt32Field()
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        unique_together = (('chrom', 'start', 'end'),)
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_non_coding_constraint/all_variants'
        engine = models.MergeTree(
            primary_key=('chrom', 'start', 'end'),
            order_by=('chrom', 'start', 'end'),
        )

class ScreenAllVariantsSnvIndel(models.ClickhouseModel):
    chrom = Enum8Field(return_int=False, choices=CHROMOSOME_CHOICES, primary_key=True)
    start = models.UInt32Field()
    end = models.UInt32Field()
    region_type = models.StringField(db_column='regionType')

    class Meta:
        unique_together = (('chrom', 'start', 'end'),)
        db_table = 'GRCh38/SNV_INDEL/reference_data/screen/all_variants'
        engine = models.MergeTree(
            primary_key=('chrom', 'start', 'end'),
            order_by=('chrom', 'start', 'end'),
        )

class BaseHgmd(models.ClickhouseModel):
    HGMD_CLASSES = [(0, 'DM'), (1, 'DM?'), (2, 'DP'), (3, 'DFP'), (4, 'FP'), (5, 'R')]
    accession = models.StringField()
    classification = models.Enum8Field(return_int=False, choices=HGMD_CLASSES)

    class Meta:
        abstract = True

class HgmdAllVariantsGRCh37SnvIndel(BaseHgmd):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class HgmdAllVariantsSnvIndel(BaseHgmd):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class HgmdSeqrVariantsGRCh37SnvIndel(BaseHgmd):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HgmdSeqrVariantsSnvIndel(BaseHgmd):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HgmdGRCh37SnvIndel(BaseHgmd):
    key = ForeignKey('EntriesGRCh37SnvIndel', db_column='key', related_name='hgmd_join', primary_key=True, on_delete=PROTECT)

    class Meta():
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd'
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

class HgmdSnvIndel(BaseHgmd):
    key = ForeignKey('EntriesSnvIndel', db_column='key', related_name='hgmd_join', primary_key=True, on_delete=PROTECT)

    class Meta():
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd'
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

class BaseTopmed(models.ClickhouseModel):
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    het = models.UInt32Field()
    hom = models.UInt32Field()

    class Meta:
        abstract = True

class TopmedAllVariantsGRCh37SnvIndel(BaseTopmed):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class TopmedAllVariantsSnvIndel(BaseTopmed):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class TopmedSeqrVariantsGRCh37SnvIndel(BaseTopmed):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class TopmedSeqrVariantsSnvIndel(BaseTopmed):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseGnomad(models.ClickhouseModel):
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    filter_af = models.DecimalField(max_digits=9, decimal_places=8)
    hemi = models.UInt32Field()
    hom = models.UInt32Field()

    class Meta:
        abstract = True

class GnomadExomesAllVariantsGRCh37SnvIndel(BaseGnomad):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadExomesAllVariantsSnvIndel(BaseGnomad):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadExomesSeqrVariantsGRCh37SnvIndel(BaseGnomad):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadExomesSeqrVariantsSnvIndel(BaseGnomad):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadGenomesAllVariantsGRCh37SnvIndel(BaseGnomad):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadGenomesAllVariantsSnvIndel(BaseGnomad):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadGenomesSeqrVariantsGRCh37SnvIndel(BaseGnomad):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadGenomesSeqrVariantsSnvIndel(BaseGnomad):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseSpliceAi(models.ClickhouseModel):
    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence = models.Enum8Field(return_int=False, choices=[(0, 'Acceptor gain'), (1, 'Acceptor loss'), (2, 'Donor gain'), (3, 'Donor loss'), (4, 'No consequence')])

    class Meta:
        abstract = True

class SpliceAiAllVariantsGRCh37SnvIndel(BaseSpliceAi):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class SpliceAiAllVariantsSnvIndel(BaseSpliceAi):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class SpliceAiSeqrVariantsGRCh37SnvIndel(BaseSpliceAi):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class SpliceAiSeqrVariantsSnvIndel(BaseSpliceAi):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseDbnsfp(models.ClickhouseModel):
    MUTATION_TASTER_PREDICTIONS = [(0, 'D'), (1, 'A'), (2, 'N'), (3, 'P')]

    cadd = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    fathmm = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    mpc = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    mut_pred = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    mut_taster = models.Enum8Field(null=True, blank=True, return_int=False, choices=MUTATION_TASTER_PREDICTIONS)
    polyphen = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    primate_ai = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    revel = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)
    vest = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)

    class Meta:
        abstract = True

class DbnsfpAllVariantsGRCh37SnvIndel(BaseDbnsfp):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class DbnsfpAllVariantsSnvIndel(BaseDbnsfp):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class DbnsfpSeqrVariantsGRCh37SnvIndel(BaseDbnsfp):
    key = OneToOneField('AnnotationsGRCh37SnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class DbnsfpSeqrVariantsSnvIndel(BaseDbnsfp):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HelixmitoAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/helix_mito/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class HelixmitoheteroplasmyAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    max_hl = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/helix_mito_heteroplasmy/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class HelixmitoSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/helix_mito/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HelixmitoheteroplasmySeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    max_hl = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/helix_mito_heteroplasmy/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadmitoAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadmitoheteroplasmyAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    max_hl = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito_heteroplasmy/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class GnomadmitoSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadmitoheteroplasmySeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    max_hl = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito_heteroplasmy/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HmtvarAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/hmtvar/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class HmtvarSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/hmtvar/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class MitimpactAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitimpact/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class MitimpactSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitimpact/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class LocalconstraintmitoAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class LocalconstraintmitoSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class MitomapAllVariantsMito(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    pathogenic = models.BoolField()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitomap/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class MitomapSeqrVariantsMito(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    pathogenic = models.BoolField()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitomap/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseDbnsfpMito(models.ClickhouseModel):
    MUTATION_TASTER_PREDICTIONS = [(0, 'D'), (1, 'A'), (2, 'N'), (3, 'P')]

    mut_taster = models.Enum8Field(null=True, blank=True, return_int=False, choices=MUTATION_TASTER_PREDICTIONS)
    sift = models.DecimalField(max_digits=9, decimal_places=5, blank=True, null=True)

    class Meta:
        abstract = True

class DbnsfpAllVariantsMito(BaseDbnsfpMito):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/dbnsfp/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class DbnsfpSeqrVariantsMito(BaseDbnsfpMito):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/dbnsfp/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class Absplice2AllVariants(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class Absplice2SeqrVariants(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PromoterAIAllVariants(models.ClickhouseModel):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class PromoterAIAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/all_variants_mv'
        to_table = 'PromoterAIAllVariants'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/promoterAI/promoterAI.tsv.gz'
        column_selects = {
            'variantId': "concat(replaceOne(replaceOne(chrom, 'chr', ''), 'MT', 'M'), '-', pos, '-', ref, '-', alt)",
            'geneId': 'gene_id',
            'score': 'promoterAI,'
        }
        create_empty = True

class PromoterAISeqrVariants(models.ClickhouseModel):
    key = OneToOneField('AnnotationsMito', db_column='key', primary_key=True, on_delete=CASCADE)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PromoterAIMv(RefreshableMaterializedView):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/all_variants_to_seqr_variants_mv'
        to_table = 'PromoterAISeqrVariants'
        source_table = 'PromoterAIAllVariants'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'SNV_INDEL')
        column_selects = {
            'key': 'DISTINCT ON (key)',
        }
        create_empty = True
