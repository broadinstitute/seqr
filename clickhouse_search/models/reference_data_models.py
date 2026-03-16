from clickhouse_backend import models
from django.db.models import ForeignKey, OneToOneField, CASCADE, PROTECT
import requests

from clickhouse_search.backend.engines import Join
from clickhouse_search.backend.fields import Enum8Field, NestedField, UInt32FieldDeltaCodecField, DictKeyForeignKey
from clickhouse_search.backend.table_models import FixtureLoadableClickhouseModel, Dictionary, \
    RefreshableMaterializedView, RefreshableMaterializedViewMeta
from seqr.utils.xpos_utils import CHROMOSOME_CHOICES
from settings import DATABASES, PIPELINE_RUNNER_SERVER


def conditionally_refresh_reference_dataset(reference_dataset: str):
    def inner(apps, schema_editor):
        if DATABASES['default']['NAME'].startswith('test_'):
            return
        requests.post( # pragma: no cover
            f"{PIPELINE_RUNNER_SERVER}/refresh_clickhouse_reference_dataset_enqueue",
            json={"reference_dataset": reference_dataset},
            timeout=60,
        )
    return inner


def _all_variants_to_seqr_source_sql(reference_genome, dataset_type):
    return f'src INNER JOIN `{reference_genome}/{dataset_type}/key_lookup` dst on assumeNotNull(src.variantId) = dst.variantId'


class ReferenceDataMvMeta(RefreshableMaterializedViewMeta):
    source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'SNV_INDEL')
    column_selects = {
        'key': 'DISTINCT ON (key)',
    }
    create_empty = True

class ReferenceDataDictMeta:
    engine = models.MergeTree(primary_key='key')
    layout = 'HASHED_ARRAY()'


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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/clinvar/seqr_variants'
        engine = models.MergeTree(
            primary_key='key',
            order_by='key'
        )

class ClinvarSeqrVariantsSnvIndel(BaseClinvar):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    class Meta(BaseClinvar.Meta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants'
        engine = models.MergeTree(
            primary_key='key',
            order_by='key'
        )

class ClinvarSeqrVariantsMito(BaseClinvar):
    key = UInt32FieldDeltaCodecField(primary_key=True)
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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PextSeqrVariantsMito(models.ClickhouseModel):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/pext/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PextSnvIndelAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext/all_variants_mv'
        to_table = 'PextAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/pext/gnomad.pext.gtex_v10.annotation_level.tsv.gz'
        column_selects = {
            'variantId': "concat(replaceOne(splitByChar(':', assumeNotNull(locus))[1], 'chr', ''), '-', splitByChar(':', assumeNotNull(locus))[2], '-', JSONExtract(assumeNotNull(alleles), 'Array(String)')[1], '-', JSONExtract(assumeNotNull(alleles), 'Array(String)')[2])",
            'score': "if(exp_prop_mean IN ('NaN', 'nan', ''), NULL, exp_prop_mean)",
        }
        source_sql = 'WHERE score IS NOT NULL'
        create_empty = True

class PextSnvIndelMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext/all_variants_to_seqr_variants_mv'
        to_table = 'PextSeqrVariantsSnvIndel'
        source_table = 'PextAllVariantsSnvIndel'

class PextSnvIndelDict(Dictionary):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='pext')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/pext'
        source_table = 'PextSeqrVariantsSnvIndel'

class PextMitoAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/MITO/reference_data/pext/all_variants_mv'
        to_table = 'PextAllVariantsMito'
        source_url = 'https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/pext/gnomad.pext.gtex_v10.annotation_level.tsv.gz'
        column_selects = {
            'variantId': "concat(replaceOne(splitByChar(':', assumeNotNull(locus))[1], 'chr', ''), '-', splitByChar(':', assumeNotNull(locus))[2], '-', JSONExtract(assumeNotNull(alleles), 'Array(String)')[1], '-', JSONExtract(assumeNotNull(alleles), 'Array(String)')[2])",
            'score': "if(exp_prop_mean IN ('NaN', 'nan', ''), NULL, exp_prop_mean)",
        }
        source_sql = "WHERE score IS NOT NULL AND startsWith(locus, 'chrM')"
        create_empty = True

class PextMitoMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/pext/all_variants_to_seqr_variants_mv'
        to_table = 'PextSeqrVariantsMito'
        source_table = 'PextAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class PextMitoDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='pext')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/pext'
        source_table = 'PextSeqrVariantsMito'

class GnomadNonCodingConstraintAllVariantsSnvIndel(FixtureLoadableClickhouseModel):
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

class GnomadNonCodingConstraintAllMv(RefreshableMaterializedView):
    chrom = models.StringField(null=True, blank=True)
    start = models.UInt32Field(primary_key=True)
    end = models.UInt32Field()
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_non_coding_constraint/all_variants_mv'
        to_table = 'GnomadNonCodingConstraintAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/gcp-public-data--gnomad/release/3.1/secondary_analyses/genomic_constraint/constraint_z_genome_1kb.qc.download.txt.gz'
        column_selects = {
            'chrom': "replaceOne(chrom, 'chr', '')",
            'start': 'toUInt32(assumeNotNull(start))',
            'end': 'toUInt32(assumeNotNull(end))',
            'score': 'z',
        }
        create_empty = True

class GnomadNonCodingConstraintDict(Dictionary):
    chrom_id = models.Int8Field(primary_key=True)
    start = models.UInt32Field()
    end = models.UInt32Field()
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_non_coding_constraint'
        source_table = 'GnomadNonCodingConstraintAllVariantsSnvIndel'
        engine = models.MergeTree(primary_key='chrom_id')
        layout = 'RANGE_HASHED()'
        clickhouse_query_template = 'SELECT indexOf([{chromosomes}], chrom) as chrom_id, start, end, score from {{table}}'.format( # nosec
            chromosomes=', '.join([f"\\'{chrom}\\'" for _, chrom in CHROMOSOME_CHOICES])
        )

class ScreenAllVariantsSnvIndel(FixtureLoadableClickhouseModel):
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

class ScreenAllMv(RefreshableMaterializedView):
    chrom = models.StringField(null=True, blank=True)
    start = models.UInt32Field(primary_key=True)
    end = models.UInt32Field()
    region_type = models.StringField(db_column='regionType')

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/screen/all_variants_mv'
        to_table = 'ScreenAllVariantsSnvIndel'
        # Original file sourced from `https://downloads.wenglab.org/V3/GRCh38-cCREs.bed`
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/screen/GRCh38-cCREs.bed'
        column_selects = {
            'chrom': "replaceOne(c1, 'chr', '')",
            'start': 'toUInt32(assumeNotNull(c2))',
            'end': 'toUInt32(assumeNotNull(c3))',
            'regionType': "splitByChar(',', assumeNotNull(c6))[1]",
        }
        create_empty = True

class ScreenDict(Dictionary):
    chrom = models.StringField(primary_key=True)
    start = models.UInt32Field()
    end = models.UInt32Field()
    region_type = models.StringField(db_column='regionType')

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/screen'
        source_table = 'ScreenAllVariantsSnvIndel'
        engine = models.MergeTree(primary_key='chrom')
        layout = 'RANGE_HASHED()'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HgmdSeqrVariantsSnvIndel(BaseHgmd):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HgmdGRCh37SnvIndel(BaseHgmd):
    key = ForeignKey('VariantsGRCh37SnvIndel', db_column='key', related_name='hgmd_join', primary_key=True, on_delete=PROTECT)

    class Meta():
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd'
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

class HgmdSnvIndel(BaseHgmd):
    key = ForeignKey('VariantsSnvIndel', db_column='key', related_name='hgmd_join', primary_key=True, on_delete=PROTECT)

    class Meta():
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd'
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

class HgmdMvMeta(RefreshableMaterializedViewMeta):
    column_selects = {
        'variantId': "arrayStringConcat([replaceOne(replaceOne(CHROM, 'chr', ''), 'MT', 'M'), toString(POS), REF, ALT], '-')",
        'accession': 'ID',
        'classification': "extract(INFO, 'CLASS=([^;]+)')",
    }
    source_sql = "WHERE ALT != '<DEL>' SETTINGS input_format_allow_errors_ratio = 0.01, input_format_allow_errors_num = 25"
    create_empty = True

HGMD_INFO_STRUCTURE = 'CHROM String, POS UInt32, ID String, REF String, ALT String, QUAL String, FILTER String, INFO String'

def _hgmd_source(url):
    # TODO
    if not url:
        return f"null('{HGMD_INFO_STRUCTURE}')"
    return f"gcs(pipeline_data_access, url='{url}', format='TSV', structure='{HGMD_INFO_STRUCTURE}')"


class HgmdAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    accession = models.StringField()
    classification = models.StringField()

    class Meta(HgmdMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/all_variants_mv'
        to_table = 'HgmdAllVariantsSnvIndel'
        source_url = '{HGMD_GRCH38_URL}'

class HgmdMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    accession = models.StringField()
    classification = models.Enum8Field(return_int=False, choices=BaseHgmd.HGMD_CLASSES)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/all_variants_to_seqr_variants_mv'
        to_table = 'HgmdSeqrVariantsSnvIndel'
        source_table = 'HgmdAllVariantsSnvIndel'

class HgmdSearchMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    accession = models.StringField()
    classification = models.Enum8Field(return_int=False, choices=BaseHgmd.HGMD_CLASSES)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/hgmd/seqr_variants_to_search_mv'
        to_table = 'HgmdSnvIndel'
        source_table = 'HgmdSeqrVariantsSnvIndel'
        column_selects = {
            'key': 'DISTINCT ON (key)',
        }

class HgmdGRCh37AllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    accession = models.StringField()
    classification = models.StringField()

    class Meta(HgmdMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/all_variants_mv'
        to_table = 'HgmdAllVariantsGRCh37SnvIndel'
        source_url = '{HGMD_GRCH37_URL}'

class HgmdGRCh37Mv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    accession = models.StringField()
    classification = models.Enum8Field(return_int=False, choices=BaseHgmd.HGMD_CLASSES)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/all_variants_to_seqr_variants_mv'
        to_table = 'HgmdSeqrVariantsGRCh37SnvIndel'
        source_table = 'HgmdAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class HgmdGRCh37SearchMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    accession = models.StringField()
    classification = models.Enum8Field(return_int=False, choices=BaseHgmd.HGMD_CLASSES)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/hgmd/seqr_variants_to_search_mv'
        to_table = 'HgmdGRCh37SnvIndel'
        source_table = 'HgmdSeqrVariantsGRCh37SnvIndel'
        column_selects = {
            'key': 'DISTINCT ON (key)',
        }

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class TopmedSeqrVariantsSnvIndel(BaseTopmed):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BasePopulationAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.Int32Field(null=True, blank=True)
    af = models.Float32Field(null=True, blank=True)
    an = models.Int32Field(null=True, blank=True)
    hom = models.Int32Field(null=True, blank=True)

    class Meta:
        abstract = True

class BasePopulationMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    hom = models.UInt32Field()

    class Meta:
        abstract = True

class BasePopulationDict(Dictionary):
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()
    hom = models.UInt32Field()

    class Meta:
        abstract = True

class PopulationMvMeta(RefreshableMaterializedViewMeta):
    column_selects = {
        'variantId': 'assumeNotNull(variant_id)',
        'ac': 'AC',
        'af': 'AF',
        'an': 'AN',
        'filter_af': 'AF_POPMAX_OR_GLOBAL',
        'hemi': 'Hemi',
        'hom': 'Hom',
        'het': 'Het',
    }
    create_empty = True

class TopmedAllMv(BasePopulationAllMv):
    het = models.Int32Field(null=True, blank=True)

    class Meta(PopulationMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed/all_variants_mv'
        to_table = 'TopmedAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/topmed/1.1.parquet/*.parquet'

class TopmedMv(BasePopulationMv):
    het = models.UInt32Field()

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed/all_variants_to_seqr_variants_mv'
        to_table = 'TopmedSeqrVariantsSnvIndel'
        source_table = 'TopmedAllVariantsSnvIndel'

class TopmedDict(BasePopulationDict):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='topmed')
    het = models.UInt32Field()

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/topmed'
        source_table = 'TopmedSeqrVariantsSnvIndel'

class TopmedGRCh37AllMv(BasePopulationAllMv):
    het = models.Int32Field(null=True, blank=True)

    class Meta(PopulationMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed/all_variants_mv'
        to_table = 'TopmedAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh37/topmed/1.1.parquet/*.parquet'

class TopmedGRCh37Mv(BasePopulationMv):
    het = models.UInt32Field()

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed/all_variants_to_seqr_variants_mv'
        to_table = 'TopmedSeqrVariantsGRCh37SnvIndel'
        source_table = 'TopmedAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class TopmedGRCh37Dict(BasePopulationDict):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='topmed')
    het = models.UInt32Field()

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/topmed'
        source_table = 'TopmedSeqrVariantsGRCh37SnvIndel'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadExomesSeqrVariantsSnvIndel(BaseGnomad):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseGnomadAllMv(BasePopulationAllMv):
    filter_af = models.Float32Field(null=True, blank=True)
    hemi = models.Int32Field(null=True, blank=True)

    class Meta:
        abstract = True

class BaseGnomadMv(BasePopulationMv):
    filter_af = models.DecimalField(max_digits=9, decimal_places=8)
    hemi = models.UInt32Field()

    class Meta:
        abstract = True

class BaseGnomadDict(BasePopulationDict):
    filter_af = models.DecimalField(max_digits=9, decimal_places=8)
    hemi = models.UInt32Field()

    class Meta:
        abstract = True

class GnomadExomesAllMv(BaseGnomadAllMv):
    class Meta(PopulationMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes/all_variants_mv'
        to_table = 'GnomadExomesAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/gnomad_exomes/1.0.parquet/*.parquet'

class GnomadExomesMv(BaseGnomadMv):
    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadExomesSeqrVariantsSnvIndel'
        source_table = 'GnomadExomesAllVariantsSnvIndel'

class GnomadExomesDict(BaseGnomadDict):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='gnomad_exomes')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_exomes'
        source_table = 'GnomadExomesSeqrVariantsSnvIndel'

class GnomadExomesGRCh37AllMv(BaseGnomadAllMv):
    class Meta(PopulationMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes/all_variants_mv'
        to_table = 'GnomadExomesAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh37/gnomad_exomes/1.0.parquet/*.parquet'

class GnomadExomesGRCh37Mv(BaseGnomadMv):
    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadExomesSeqrVariantsGRCh37SnvIndel'
        source_table = 'GnomadExomesAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class GnomadExomesGRCh37Dict(BaseGnomadDict):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='gnomad_exomes')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_exomes'
        source_table = 'GnomadExomesSeqrVariantsGRCh37SnvIndel'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadGenomesSeqrVariantsSnvIndel(BaseGnomad):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class GnomadGenomesAllMv(BaseGnomadAllMv):

    class Meta(PopulationMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes/all_variants_mv'
        to_table = 'GnomadGenomesAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/gnomad_genomes/1.0.parquet/*.parquet'

class GnomadGenomesMv(BaseGnomadMv):

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadGenomesSeqrVariantsSnvIndel'
        source_table = 'GnomadGenomesAllVariantsSnvIndel'

class GnomadGenomesDict(BaseGnomadDict):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='gnomad_genomes')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/gnomad_genomes'
        source_table = 'GnomadGenomesSeqrVariantsSnvIndel'

class GnomadGenomesGRCh37AllMv(BaseGnomadAllMv):

    class Meta(PopulationMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes/all_variants_mv'
        to_table = 'GnomadGenomesAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh37/gnomad_genomes/1.0.parquet/*.parquet'

class GnomadGenomesGRCh37Mv(BaseGnomadMv):

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadGenomesSeqrVariantsGRCh37SnvIndel'
        source_table = 'GnomadGenomesAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class GnomadGenomesGRCh37Dict(BaseGnomadDict):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='gnomad_genomes')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/gnomad_genomes'
        source_table = 'GnomadGenomesSeqrVariantsGRCh37SnvIndel'

class BaseSpliceAi(models.ClickhouseModel):
    CONSEQUENCE_CHOICES = [(0, 'Acceptor gain'), (1, 'Acceptor loss'), (2, 'Donor gain'), (3, 'Donor loss'), (4, 'No consequence')]

    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence = models.Enum8Field(return_int=False, choices=CONSEQUENCE_CHOICES)

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class SpliceAiSeqrVariantsSnvIndel(BaseSpliceAi):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class SpliceAiMvMeta(RefreshableMaterializedViewMeta):
    column_selects = {
        'variantId': 'assumeNotNull(variant_id)',
        'score': 'delta_score',
        'consequence': 'splice_consequence_id',
    }
    create_empty = True

class SpliceAiAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.Float32Field(null=True, blank=True)
    consequence = models.Int32Field(null=True, blank=True)

    class Meta(SpliceAiMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai/all_variants_mv'
        to_table = 'SpliceAiAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/splice_ai/1.1.parquet/*.parquet'

class SpliceAiMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence = models.Enum8Field(return_int=False, choices=BaseSpliceAi.CONSEQUENCE_CHOICES)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai/all_variants_to_seqr_variants_mv'
        to_table = 'SpliceAiSeqrVariantsSnvIndel'
        source_table = 'SpliceAiAllVariantsSnvIndel'

class SpliceAiDict(Dictionary):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='splice_ai')
    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence_id = models.UInt8Field(null=True, blank=True)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/splice_ai'
        source_table = 'SpliceAiSeqrVariantsSnvIndel'
        clickhouse_query_template = 'SELECT key, score, toUInt8(consequence) from {table}'

class SpliceAiGRCh37AllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.Float32Field(null=True, blank=True)
    consequence = models.Int32Field(null=True, blank=True)

    class Meta(SpliceAiMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai/all_variants_mv'
        to_table = 'SpliceAiAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh37/splice_ai/1.1.parquet/*.parquet'

class SpliceAiGRCh37Mv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence = models.Enum8Field(return_int=False, choices=BaseSpliceAi.CONSEQUENCE_CHOICES)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai/all_variants_to_seqr_variants_mv'
        to_table = 'SpliceAiSeqrVariantsGRCh37SnvIndel'
        source_table = 'SpliceAiAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class SpliceAiGRCh37Dict(Dictionary):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='splice_ai')
    score = models.DecimalField(max_digits=9, decimal_places=5)
    consequence_id = models.UInt8Field(null=True, blank=True)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/splice_ai'
        source_table = 'SpliceAiSeqrVariantsGRCh37SnvIndel'
        clickhouse_query_template = 'SELECT key, score, toUInt8(consequence) from {table}'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class DbnsfpSeqrVariantsSnvIndel(BaseDbnsfp):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class BaseDbnsfpMv(RefreshableMaterializedView):
    cadd = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    fathmm = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mpc = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mut_pred = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mut_taster = models.StringField(null=True, blank=True)
    polyphen = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    primate_ai = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    revel = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    vest = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)

    class Meta:
        abstract = True

class DbnsfpAllMvMeta(RefreshableMaterializedViewMeta):
    source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/dbnsfp/dbNSFP5.3a_grch38.gz'
    source_url_template = "gcs('{source_url}', 'TabSeparatedWithNames')"
    column_selects = {
        'variantId': "assumeNotNull(concat(`#chr`, '-', `pos(1-based)`, '-', ref, '-', alt))",
        'mut_taster': "nullIf(arrayFirst(x -> (x != '.'), splitByChar(';', assumeNotNull(`c`))), '')",
        **{score: f'CAST(`{score_col}` as Nullable(Decimal(9, 5)))' for score, score_col in [
            ('cadd', 'CADD_phred'),
            ('fathmm', 'fathmm-XF_coding_score'),
            ('primate_ai', 'PrimateAI_score'),
        ]},
        **{score: f"CAST(arrayFirst(x -> (x != '.'), splitByChar(';', assumeNotNull(`{score_col}`))) as Nullable(Decimal(9, 5)))" for score, score_col in [
            ('mpc', 'MPC_score'),
            ('mut_pred', 'MutPred2_score'),
            ('polyphen', 'Polyphen2_HVAR_score'),
            ('revel', 'REVEL_score'),
            ('sift', 'SIFT_score'),
            ('vest', 'VEST4_score'),
        ]},
    }
    create_empty = True

class BaseDbnsfpDict(Dictionary):
    cadd = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    fathmm = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mpc = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mut_pred = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    mut_taster = models.StringField(null=True, blank=True)
    polyphen = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    primate_ai = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    revel = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    vest = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)

    class Meta:
        abstract = True

class DbnsfpSnvIndelAllMv(BaseDbnsfpMv):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta(DbnsfpAllMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp/all_variants_mv'
        to_table = 'DbnsfpAllVariantsSnvIndel'
        source_sql = "WHERE (`#chr` != 'M') AND (arrayExists(x -> (x IS NOT NULL), [cadd, fathmm, mpc, mut_pred, polyphen, primate_ai, revel, sift, vest]) OR (mut_taster IS NOT NULL)) SETTINGS input_format_tsv_use_best_effort_in_schema_inference = 0"

class DbnsfpSnvIndelMv(BaseDbnsfpMv):
    key = models.UInt32Field(primary_key=True)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp/all_variants_to_seqr_variants_mv'
        to_table = 'DbnsfpSeqrVariantsSnvIndel'
        source_table = 'DbnsfpAllVariantsSnvIndel'

class DbnsfpSnvIndelDict(BaseDbnsfpDict):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='dbnsfp')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/dbnsfp'
        source_table = 'DbnsfpSeqrVariantsSnvIndel'

class DbnsfpGRCh37SnvIndelAllMv(BaseDbnsfpMv):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta(DbnsfpAllMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp/all_variants_mv'
        to_table = 'DbnsfpAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh37/dbnsfp/dbNSFP5.3a_grch37.gz'
        source_sql = "WHERE (arrayExists(x -> isNotNull(x), [cadd, fathmm, mpc, mut_pred, polyphen, primate_ai, revel, sift, vest]) OR isNotNull(mut_taster)) SETTINGS input_format_tsv_use_best_effort_in_schema_inference = 0"
        column_selects = {
            **DbnsfpAllMvMeta.column_selects,
            'variantId': "assumeNotNull(concat(`hg19_chr`, '-', `hg19_pos(1-based)`, '-', ref, '-', alt))",
        }

class DbnsfpGRCh37SnvIndelMv(BaseDbnsfpMv):
    key = models.UInt32Field(primary_key=True)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp/all_variants_to_seqr_variants_mv'
        to_table = 'DbnsfpSeqrVariantsGRCh37SnvIndel'
        source_table = 'DbnsfpAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class DbnsfpGRCh37SnvIndelDict(BaseDbnsfpDict):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='dbnsfp')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/dbnsfp'
        source_table = 'DbnsfpSeqrVariantsGRCh37SnvIndel'

class DbnsfpMitoAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    mut_taster = models.StringField(null=True, blank=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)

    class Meta(DbnsfpAllMvMeta):
        db_table = 'GRCh38/MITO/reference_data/dbnsfp/all_variants_mv'
        to_table = 'DbnsfpAllVariantsMito'
        source_sql = "WHERE `#chr` = 'M' AND isNotNull(sift) OR isNotNull(mut_taster) SETTINGS input_format_tsv_use_best_effort_in_schema_inference = 0"

class DbnsfpMitoMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    mut_taster = models.StringField(null=True, blank=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/dbnsfp/all_variants_to_seqr_variants_mv'
        to_table = 'DbnsfpSeqrVariantsMito'
        source_table = 'DbnsfpAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class DbnsfpMitoDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='dbnsfp')
    mut_taster = models.StringField(null=True, blank=True)
    sift = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/dbnsfp'
        source_table = 'DbnsfpSeqrVariantsMito'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
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
    key = UInt32FieldDeltaCodecField(primary_key=True)
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

class BaseMitoPopulationMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        abstract = True

class BaseMitoPopulationDict(Dictionary):
    ac = models.UInt32Field()
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.UInt32Field()

    class Meta:
        abstract = True

class HelixmitoMvMeta(RefreshableMaterializedViewMeta):
    source_url = 'https://helix-research-public.s3.amazonaws.com/mito/HelixMTdb_20200327.tsv'
    column_selects = {
        'variantId': "assumeNotNull(concat('M', '-', replace(locus, 'chrM:', ''), '-', arrayStringConcat(arrayMap(x -> replaceAll(x, '\"', ''), JSONExtractArrayRaw(assumeNotNull(alleles))), '-')))",
        'ac': 'counts_hom',
        'af': 'CAST(AF_hom AS Decimal(9, 8))',
        'an': 'if(toFloat64(AF_hom) > 0, CAST(counts_hom / toFloat64(AF_hom) AS Int32), CAST(counts_het / toFloat64(AF_het) AS Int32))',
    }
    create_empty = True

class HelixmitoAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.Int64Field(null=True, blank=True)
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.Int32Field()

    class Meta(HelixmitoMvMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito/all_variants_mv'
        to_table = 'HelixmitoAllVariantsMito'

class HelixmitoheteroplasmyAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.Int64Field(null=True, blank=True)
    af = models.DecimalField(max_digits=9, decimal_places=8)
    an = models.Int32Field()
    max_hl = models.StringField(null=True, blank=True)

    class Meta(HelixmitoMvMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito_heteroplasmy/all_variants_mv'
        to_table = 'HelixmitoheteroplasmyAllVariantsMito'
        column_selects = {
            **HelixmitoMvMeta.column_selects,
            'ac': 'counts_het',
            'af': 'CAST(AF_het AS Decimal(9, 8))',
            'max_hl': 'max_ARF',
        }

class HelixmitoMv(BaseMitoPopulationMv):

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito/all_variants_to_seqr_variants_mv'
        to_table = 'HelixmitoSeqrVariantsMito'
        source_table = 'HelixmitoAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class HelixmitoheteroplasmyMv(BaseMitoPopulationMv):
    max_hl = models.DecimalField(max_digits=9, decimal_places=8)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito_heteroplasmy/all_variants_to_seqr_variants_mv'
        to_table = 'HelixmitoheteroplasmySeqrVariantsMito'
        source_table = 'HelixmitoheteroplasmyAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class HelixmitoDict(BaseMitoPopulationDict):
    key = DictKeyForeignKey('EntriesMito', related_name='helix')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito'
        source_table = 'HelixmitoSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

class HelixmitoheteroplasmyDict(BaseMitoPopulationDict):
    key = DictKeyForeignKey('EntriesMito', related_name='helix_heteroplasmy')
    max_hl = models.DecimalField(max_digits=9, decimal_places=8)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/helix_mito_heteroplasmy'
        source_table = 'HelixmitoheteroplasmySeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
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
    key = UInt32FieldDeltaCodecField(primary_key=True)
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

class GnomadmitoMvMeta(RefreshableMaterializedViewMeta):
    source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/gnomad_mito/1.1.parquet/*.parquet'
    column_selects = {
        'variantId': 'assumeNotNull(variant_id)',
        'ac': 'AC_hom',
        'af': 'AF_hom',
        'an': 'AN',
    }
    create_empty = True

class GnomadmitoAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.Int32Field(null=True, blank=True)
    af = models.Float32Field(null=True, blank=True)
    an = models.Int32Field(null=True, blank=True)

    class Meta(GnomadmitoMvMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito/all_variants_mv'
        to_table = 'GnomadmitoAllVariantsMito'

class GnomadmitoheteroplasmyAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    ac = models.Int32Field(null=True, blank=True)
    af = models.Float32Field(null=True, blank=True)
    an = models.Int32Field(null=True, blank=True)
    max_hl = models.Float32Field(null=True, blank=True)

    class Meta(GnomadmitoMvMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito_heteroplasmy/all_variants_mv'
        to_table = 'GnomadmitoheteroplasmyAllVariantsMito'
        column_selects = {
            **GnomadmitoMvMeta.column_selects,
            'ac': 'AC_het',
        }

class GnomadmitoMv(BaseMitoPopulationMv):

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadmitoSeqrVariantsMito'
        source_table = 'GnomadmitoAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class GnomadmitoheteroplasmyMv(BaseMitoPopulationMv):
    max_hl = models.DecimalField(max_digits=9, decimal_places=8)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito_heteroplasmy/all_variants_to_seqr_variants_mv'
        to_table = 'GnomadmitoheteroplasmySeqrVariantsMito'
        source_table = 'GnomadmitoheteroplasmyAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class GnomadmitoDict(BaseMitoPopulationDict):
    key = DictKeyForeignKey('EntriesMito', related_name='gnomad_mito')

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito'
        source_table = 'GnomadmitoSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

class GnomadmitoheteroplasmyDict(BaseMitoPopulationDict):
    key = DictKeyForeignKey('EntriesMito', related_name='gnomad_mito_heteroplasmy')
    max_hl = models.DecimalField(max_digits=9, decimal_places=8)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/gnomad_mito_heteroplasmy'
        source_table = 'GnomadmitoheteroplasmySeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/hmtvar/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class HmtvarAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/MITO/reference_data/hmtvar/all_variants_mv'
        to_table = 'HmtvarAllVariantsMito'
        source_url_template = "(SELECT concat('M', '-', nt_start, '-', ref_rCRS, '-', alt) as variantId, CAST(disease_score AS Decimal(9, 5)) AS score FROM url('{source_url}') WHERE match(alt, '^[ACTG]+$$') AND (disease_score IS NOT NULL))"
        source_url = 'https://storage.googleapis.com/seqr-reference-data/GRCh38/mitochondrial/HmtVar/HmtVar%20Jan.%2010%202022.json'
        column_selects = {
            'score': 'max(score)',
        }
        source_sql = 'GROUP BY variantId'
        create_empty = True

class HmtvarMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/hmtvar/all_variants_to_seqr_variants_mv'
        to_table = 'HmtvarSeqrVariantsMito'
        source_table = 'HmtvarAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class HmtvarDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='hmtvar')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/hmtvar'
        source_table = 'HmtvarSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitimpact/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class MitimpactAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/MITO/reference_data/mitimpact/all_variants_mv'
        to_table = 'MitimpactAllVariantsMito'
        source_url_template = "(SELECT concat('M', '-', Start, '-', Ref, '-', Alt) as variantId, CAST(APOGEE2_score AS Decimal(9, 5)) AS score FROM url('{source_url}', 'TSV'))"
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/mitimpact/MitImpact_db_3.1.3.txt'
        column_selects = {
            'score': 'max(score)',
        }
        source_sql = 'GROUP BY variantId SETTINGS input_format_tsv_crlf_end_of_line = 1'
        create_empty = True

class MitimpactMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/mitimpact/all_variants_to_seqr_variants_mv'
        to_table = 'MitimpactSeqrVariantsMito'
        source_table = 'MitimpactAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class MitimpactDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='apogee')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/mitimpact'
        source_table = 'MitimpactSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class LocalconstraintmitoAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito/all_variants_mv'
        to_table = 'LocalconstraintmitoAllVariantsMito'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/local_constraint_mito/supplementary_dataset_7.tsv'
        column_selects = {
            'variantId': "concat('M', '-', Position, '-', Reference, '-', Alternate)",
            'score': 'CAST(MLC_score AS Decimal(9, 5))',
        }
        create_empty = True

class LocalconstraintmitoMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito/all_variants_to_seqr_variants_mv'
        to_table = 'LocalconstraintmitoSeqrVariantsMito'
        source_table = 'LocalconstraintmitoAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class LocalconstraintmitoDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='mlc')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/local_constraint_mito'
        source_table = 'LocalconstraintmitoSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    pathogenic = models.BoolField()

    class Meta:
        db_table = 'GRCh38/MITO/reference_data/mitomap/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class MitomapAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    pathogenic = models.BoolField()

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/MITO/reference_data/mitomap/all_variants_mv'
        to_table = 'MitomapAllVariantsMito'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/GRCh38/mitochondrial/MITOMAP/mitomap_confirmed_mutations_nov_2024.csv'
        source_url_template = "url('{source_url}', 'CsvWithNames')"
        column_selects = {
            'variantId': "concat('M', '-', Position, '-', extract(assumeNotNull(Allele), 'm\\.[0-9]+([ATGC]+)>[ATGC]+'), '-', extract(assumeNotNull(Allele), 'm\\.[0-9]+[ATGC]+>([ATGC]+)'))",
            'pathogenic': 'true',
        }
        source_sql = "WHERE variantId NOT LIKE '%--'"
        create_empty = True

class MitomapMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    pathogenic = models.BoolField()

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/MITO/reference_data/mitomap/all_variants_to_seqr_variants_mv'
        to_table = 'MitomapSeqrVariantsMito'
        source_table = 'MitomapAllVariantsMito'
        source_sql = _all_variants_to_seqr_source_sql('GRCh38', 'MITO')

class MitomapDict(Dictionary):
    key = DictKeyForeignKey('EntriesMito', related_name='mitomap')
    pathogenic = models.BoolField()

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/MITO/reference_data/mitomap'
        source_table = 'MitomapSeqrVariantsMito'
        layout = 'FLAT(MAX_ARRAY_SIZE 1e6)'


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
    key = UInt32FieldDeltaCodecField(primary_key=True)

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
    key = UInt32FieldDeltaCodecField(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class Absplice2AllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2/all_variants_mv'
        to_table = 'Absplice2AllVariants'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/absplice2/absplice2.tsv.gz'
        column_selects = {
            'variantId': "assumeNotNull(concat(replaceOne(replaceOne(chrom, 'chr', ''), 'MT', 'M'), '-', pos, '-', ref, '-', alt))",
            'score': 'AbSplice_DNA_max'
        }
        create_empty = True

class Absplice2Mv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2/all_variants_to_seqr_variants_mv'
        to_table = 'Absplice2SeqrVariants'
        source_table = 'Absplice2AllVariants'

class Absplice2Dict(Dictionary):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='absplice')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/absplice2'
        source_table = 'Absplice2SeqrVariants'

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

class PromoterAISeqrVariants(models.ClickhouseModel):
    key = UInt32FieldDeltaCodecField(primary_key=True)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class PromoterAIAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    gene_id = models.StringField(db_column='geneId', null=True, blank=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/all_variants_mv'
        to_table = 'PromoterAIAllVariants'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/clickhouse/GRCh38/promoterAI/promoterAI.tsv.gz'
        column_selects = {
            'variantId': "assumeNotNull(concat(replaceOne(replaceOne(chrom, 'chr', ''), 'MT', 'M'), '-', pos, '-', ref, '-', alt))",
            'geneId': 'gene_id',
            'score': 'promoterAI'
        }
        create_empty = True

class PromoterAIMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    gene_id = models.StringField(db_column='geneId')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI/all_variants_to_seqr_variants_mv'
        to_table = 'PromoterAISeqrVariants'
        source_table = 'PromoterAIAllVariants'

class PromoterAIDict(Dictionary):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='promoter_ai')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/promoterAI'
        source_table = 'PromoterAISeqrVariants'
        clickhouse_query_template = 'SELECT key, max(score) from {table} GROUP BY key'

class BaseEigen(models.ClickhouseModel):
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta:
        abstract = True

class EigenAllVariantsGRCh37SnvIndel(BaseEigen):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/eigen/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class EigenAllVariantsSnvIndel(BaseEigen):
    variant_id = models.StringField(db_column='variantId', primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/eigen/all_variants'
        engine = models.MergeTree(
            primary_key=('variant_id'),
            order_by=('variant_id'),
        )

class EigenSeqrVariantsGRCh37SnvIndel(BaseEigen):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh37/SNV_INDEL/reference_data/eigen/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class EigenSeqrVariantsSnvIndel(BaseEigen):
    key = UInt32FieldDeltaCodecField(primary_key=True)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/reference_data/eigen/seqr_variants'
        engine = models.MergeTree(
            primary_key=('key'),
            order_by=('key'),
        )

class EigenGRCh37AllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/eigen/all_variants_mv'
        to_table = 'EigenAllVariantsGRCh37SnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh37/eigen/1.1.parquet/*.parquet'
        column_selects = {
            'variantId': "variant_id",
            'score': 'Eigen_phred'
        }
        create_empty = True

class EigenGRCh37Mv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/eigen/all_variants_to_seqr_variants_mv'
        to_table = 'EigenSeqrVariantsGRCh37SnvIndel'
        source_table = 'EigenAllVariantsGRCh37SnvIndel'
        source_sql = _all_variants_to_seqr_source_sql('GRCh37', 'SNV_INDEL')

class EigenGRCh37Dict(Dictionary):
    key = DictKeyForeignKey('EntriesGRCh37SnvIndel', related_name='eigen')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh37/SNV_INDEL/reference_data/eigen'
        source_table = 'EigenSeqrVariantsGRCh37SnvIndel'
        layout = 'FLAT(MAX_ARRAY_SIZE 200000000)'

class EigenAllMv(RefreshableMaterializedView):
    variant_id = models.StringField(db_column='variantId', primary_key=True)
    score = models.StringField(null=True, blank=True)

    class Meta(RefreshableMaterializedViewMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/eigen/all_variants_mv'
        to_table = 'EigenAllVariantsSnvIndel'
        source_url = 'https://storage.googleapis.com/seqr-reference-data/v3.1/GRCh38/eigen/1.1.parquet/*.parquet'
        column_selects = {
            'variantId': "variant_id",
            'score': 'Eigen_phred'
        }
        create_empty = True

class EigenMv(RefreshableMaterializedView):
    key = models.UInt32Field(primary_key=True)
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataMvMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/eigen/all_variants_to_seqr_variants_mv'
        to_table = 'EigenSeqrVariantsSnvIndel'
        source_table = 'EigenAllVariantsSnvIndel'

class EigenDict(Dictionary):
    key = DictKeyForeignKey('EntriesSnvIndel', related_name='eigen')
    score = models.DecimalField(max_digits=9, decimal_places=5)

    class Meta(ReferenceDataDictMeta):
        db_table = 'GRCh38/SNV_INDEL/reference_data/eigen'
        source_table = 'EigenSeqrVariantsSnvIndel'
        layout = 'FLAT(MAX_ARRAY_SIZE 1000000000)'
