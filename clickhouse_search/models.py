from clickhouse_backend import models


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


class CollapsingMergeTree(models.CollapsingMergeTree):
    setting_types = {
        **models.CollapsingMergeTree.setting_types,
        _no_validate: ['deduplicate_merge_projection_mode']
    }


class EntriesGrch38SnvIndel(models.ClickhouseModel):
    project_guid = models.StringField()
    family_guid = models.StringField()
    sample_ids = models.ArrayField(models.StringField())
    key = models.UInt32Field(primary_key=True)  # primary_key has no effect on ClickHouse, but prevents Django from adding a default id column
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
        # TODO projection


#
# class Grch38SnvIndelAnnotations(models.ClickhouseModel):
#     key = models.UInt32Field(primary_key=True)
#     xpos = models.UInt64Field()
#     chrom = models.StringField(low_cardinality=True)
#     pos = models.UInt32Field()
#     ref = models.StringField()
#     alt = models.StringField()
#     variant_id = models.StringField(db_column='variantId')
#     rsid = models.StringField(null=True, blank=True)
#     caid = models.StringField(db_column='CAID', null=True, blank=True)
#     lifted_over_chrom = models.StringField(db_column='liftedOverChrom', low_cardinality=True, null=True, blank=True)
#     lifted_over_pos = models.StringField(db_column='liftedOverPos', null=True, blank=True)
#     hgmd = models.TupleField([models.accessionField()]) # TODO
#     screen_region_type = models.Enum8Field(db_column='screenRegionType', null=True, blank=True, choices=[(0, 'CTCF-bound'), (1, 'CTCF-only'), (2, 'DNase-H3K4me3'), (3, 'PLS'), (4, 'dELS'), (5, 'pELS'), (6, 'DNase-only'), (7, 'low-DNase')])
#     predictions = models.TupleField([models.caddField()]) # TODO
#     populations = models.TupleField([models.exacField()]) # TODO
#     sorted_transcript_consequences = models.NestedField(db_column='sortedTranscriptConsequences')  # TODO
#     sorted_motif_feature_consequences = models.NestedField(db_column='sortedMotifFeatureConsequences') # TODO
#     sorted_regulatory_feature_consequences = models.NestedField(db_column='sortedRegulatoryFeatureConsequences') # TODO
#
#     class Meta:
#         db_table = 'GRCh38/SNV_INDEL/annotations'
#
#
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
