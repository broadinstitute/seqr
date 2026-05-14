from clickhouse_backend import models

from clickhouse_search.backend.table_models import Dictionary


class AffectedDict(Dictionary):
    family_guid = models.StringField(primary_key=True)
    sampleId = models.StringField()
    affected = models.StringField()

    class Meta:
        db_table = 'seqrdb_affected_status_dict'
        engine = models.MergeTree(primary_key=('family_guid', 'sampleId'))
        layout = 'COMPLEX_KEY_HASHED()'
        postgres_query = 'select f.guid as family_guid, i.individual_id as sample_id, i.affected FROM seqr_individual i INNER JOIN seqr_family f ON i.family_id = f.id'


class SexDict(Dictionary):
    family_guid = models.StringField(primary_key=True)
    sampleId = models.StringField()
    sex = models.StringField()

    class Meta:
        db_table = 'seqrdb_sex_dict'
        engine = models.MergeTree(primary_key=('family_guid', 'sampleId'))
        layout = 'COMPLEX_KEY_HASHED()'
        postgres_query = 'select f.guid as family_guid, i.individual_id as sample_id, i.sex FROM seqr_individual i INNER JOIN seqr_family f ON i.family_id = f.id'


class GeneIdDict(Dictionary):
    gene_id = models.StringField(primary_key=True)
    seqrdb_id = models.UInt32Field()

    class Meta:
        db_table = 'seqrdb_gene_ids'
        engine = models.MergeTree(primary_key='gene_id')
        layout = 'HASHED()'
        postgres_db = 'reference_data'
        postgres_query = 'SELECT gene_id, id FROM reference_data_geneinfo'


class IndividualMetadataDict(Dictionary):
    family_guid = models.StringField(primary_key=True)
    sampled = models.StringField()
    restrict_sharing = models.BoolField()
    features = models.StringField()
    omim_id = models.UInt32Field()
    mondo_id = models.StringField()
    is_solved = models.BoolField()

    class Meta:
        db_table = 'seqrdb_individual_metadata_dict'
        engine = models.MergeTree(primary_key=('family_guid', 'sampleId'))
        layout = 'COMPLEX_KEY_HASHED()'
        postgres_query = "select f.guid as family_guid, i.individual_id as sampled, p.restrict_sharing as restrict_sharing, i.features as features, i.post_discovery_omim_numbers[1] as omim_id, i.post_discovery_mondo_id as mondo_id, f.analysis_status in ('S', 'S_kgfp', 'S_kgdp', 'S_ng', 'ES') as is_solved FROM seqr_individual i INNER JOIN seqr_family f ON i.family_id = f.id INNER JOIN seqr_project p ON f.project_id = p.id"


class DiscoveryVariantDict(Dictionary):
    key = models.UInt32Field(primary_key=True)
    family_guids = models.ArrayField(models.StringField())

    class Meta:
        db_table = 'seqrdb_discovery_variant_dict'
        engine = models.MergeTree(primary_key='key')
        layout = 'COMPLEX_KEY_HASHED()'
        postgres_query = "SELECT sv.key as key, array_agg(distinct f.guid) as family_guids FROM seqr_savedvariant sv INNER JOIN seqr_family f ON sv.family_id = f.id WHERE sv.id IN (SELECT savedvariant_id FROM seqr_varianttag_savedvariant vts LEFT JOIN seqr_varianttag vt ON vts.varianttag_id = vt.id LEFT JOIN seqr_varianttagtype vtt ON vt.variant_tag_type_id = vtt.id WHERE vtt.category = 'CMG Discovery Tags')"


class ExcludedVariantDict(Dictionary):
    key = models.UInt32Field(primary_key=True)
    family_guids = models.ArrayField(models.StringField())

    class Meta:
        db_table = 'seqrdb_excluded_variant_dict'
        engine = models.MergeTree(primary_key='key')
        layout = 'COMPLEX_KEY_HASHED()'
        postgres_query = "SELECT sv.key as key, array_agg(distinct f.guid) as family_guids FROM seqr_savedvariant sv INNER JOIN seqr_family f ON sv.family_id = f.id WHERE sv.id IN (SELECT savedvariant_id FROM seqr_varianttag_savedvariant vts LEFT JOIN seqr_varianttag vt ON vts.varianttag_id = vt.id LEFT JOIN seqr_varianttagtype vtt ON vt.variant_tag_type_id = vtt.id WHERE vtt.name = 'Excluded')"
