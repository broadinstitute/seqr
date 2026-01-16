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
