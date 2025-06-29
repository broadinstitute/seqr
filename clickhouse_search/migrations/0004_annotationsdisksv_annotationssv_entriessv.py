# Generated by Django 4.2.21 on 2025-06-12 20:56

import clickhouse_backend.models
import clickhouse_search.backend.engines
import clickhouse_search.backend.fields
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager

from settings import CLICKHOUSE_IN_MEMORY_DIR, CLICKHOUSE_DATA_DIR


class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0003_annotationsdiskmito_annotationsmito_entriesmito_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnotationsDiskSv',
            fields=[
                ('key', clickhouse_backend.models.UInt32Field(primary_key=True, serialize=False)),
                ('xpos', clickhouse_backend.models.UInt64Field()),
                ('chrom', clickhouse_search.backend.fields.Enum8Field(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])),
                ('pos', clickhouse_backend.models.UInt32Field()),
                ('end', clickhouse_backend.models.UInt32Field()),
                ('rg37_locus_end', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('contig', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])), ('position', clickhouse_backend.models.UInt32Field(null=True, blank=True))], db_column='rg37LocusEnd')),
                ('variant_id', clickhouse_backend.models.StringField(db_column='variantId')),
                ('lifted_over_chrom', clickhouse_search.backend.fields.Enum8Field(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')], db_column='liftedOverChrom', null=True)),
                ('lifted_over_pos', clickhouse_backend.models.UInt32Field(blank=True, db_column='liftedOverPos', null=True)),
                ('algorithms', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('bothsides_support', clickhouse_backend.models.BoolField(db_column='bothsidesSupport')),
                ('cpx_intervals', clickhouse_search.backend.fields.NestedField(base_fields=[('chrom', clickhouse_backend.models.Enum8Field(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])), ('start', clickhouse_backend.models.UInt32Field()), ('end', clickhouse_backend.models.UInt32Field()), ('type', clickhouse_backend.models.Enum8Field(choices=[(1, 'gCNV_DEL'), (2, 'gCNV_DUP'), (3, 'BND'), (4, 'CPX'), (5, 'CTX'), (6, 'DEL'), (7, 'DUP'), (8, 'INS'), (9, 'INV'), (10, 'CNV')]))], db_column='cpxIntervals')),
                ('end_chrom', clickhouse_backend.models.Enum8Field(null=True, blank=True, db_column='endChrom', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])),
                ('sv_source_detail', clickhouse_search.backend.fields.NestedField(base_fields=[('chrom', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')]))], db_column='svSourceDetail')),
                ('sv_type', clickhouse_backend.models.Enum8Field(choices=[(1, 'gCNV_DEL'), (2, 'gCNV_DUP'), (3, 'BND'), (4, 'CPX'), (5, 'CTX'), (6, 'DEL'), (7, 'DUP'), (8, 'INS'), (9, 'INV'), (10, 'CNV')], db_column='svType')),
                ('sv_type_detail', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, 'INS_iDEL'), (2, 'INVdel'), (3, 'INVdup'), (4, 'ME'), (5, 'ME:ALU'), (6, 'ME:LINE1'), (7, 'ME:SVA'), (8, 'dDUP'), (9, 'dDUP_iDEL'), (10, 'delINV'), (11, 'delINVdel'), (12, 'delINVdup'), (13, 'dupINV'), (14, 'dupINVdel'), (15, 'dupINVdup')], db_column='svTypeDetail')),
                ('predictions', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('strvctvre', clickhouse_backend.models.DecimalField(blank=True, decimal_places=5, max_digits=9, null=True))])),
                ('populations', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('gnomad_svs', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('af', clickhouse_backend.models.DecimalField(decimal_places=5, max_digits=9)), ('het', clickhouse_backend.models.UInt32Field()), ('hom', clickhouse_backend.models.UInt32Field()), ('id', clickhouse_backend.models.StringField())]))])),
                ('sorted_gene_consequences', clickhouse_search.backend.fields.NestedField(base_fields=[('geneId', clickhouse_backend.models.StringField(blank=True, null=True)), ('majorConsequence', clickhouse_backend.models.Enum8Field(blank=True, choices=[(1, 'LOF'), (2, 'INTRAGENIC_EXON_DUP'), (3, 'PARTIAL_EXON_DUP'), (4, 'COPY_GAIN'), (5, 'DUP_PARTIAL'), (6, 'MSV_EXON_OVERLAP'), (7, 'INV_SPAN'), (8, 'UTR'), (9, 'PROMOTER'), (10, 'TSS_DUP'), (11, 'BREAKEND_EXONIC'), (12, 'INTRONIC'), (13, 'NEAREST_TSS')], null=True))], db_column='sortedTranscriptConsequences')),
            ],
            options={
                'db_table': 'GRCh38/SV/annotations_disk',
                'engine': clickhouse_search.backend.engines.EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SV/annotations', flatten_nested=0, primary_key='key'),
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='AnnotationsSv',
            fields=[
                ('key', clickhouse_backend.models.UInt32Field(primary_key=True, serialize=False)),
                ('xpos', clickhouse_backend.models.UInt64Field()),
                ('chrom', clickhouse_search.backend.fields.Enum8Field(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])),
                ('pos', clickhouse_backend.models.UInt32Field()),
                ('end', clickhouse_backend.models.UInt32Field()),
                ('rg37_locus_end', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('contig', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])), ('position', clickhouse_backend.models.UInt32Field(null=True, blank=True))], db_column='rg37LocusEnd')),
                ('variant_id', clickhouse_backend.models.StringField(db_column='variantId')),
                ('lifted_over_chrom', clickhouse_search.backend.fields.Enum8Field(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')], db_column='liftedOverChrom', null=True)),
                ('lifted_over_pos', clickhouse_backend.models.UInt32Field(blank=True, db_column='liftedOverPos', null=True)),
                ('algorithms', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('bothsides_support', clickhouse_backend.models.BoolField(db_column='bothsidesSupport')),
                ('cpx_intervals', clickhouse_search.backend.fields.NestedField(base_fields=[('chrom', clickhouse_backend.models.Enum8Field(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])), ('start', clickhouse_backend.models.UInt32Field()), ('end', clickhouse_backend.models.UInt32Field()), ('type', clickhouse_backend.models.Enum8Field(choices=[(1, 'gCNV_DEL'), (2, 'gCNV_DUP'), (3, 'BND'), (4, 'CPX'), (5, 'CTX'), (6, 'DEL'), (7, 'DUP'), (8, 'INS'), (9, 'INV'), (10, 'CNV')]))], db_column='cpxIntervals')),
                ('end_chrom', clickhouse_backend.models.Enum8Field(null=True, blank=True, db_column='endChrom', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')])),
                ('sv_source_detail', clickhouse_search.backend.fields.NestedField(base_fields=[('chrom', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, 'X'), (24, 'Y'), (25, 'M')]))], db_column='svSourceDetail')),
                ('sv_type', clickhouse_backend.models.Enum8Field(choices=[(1, 'gCNV_DEL'), (2, 'gCNV_DUP'), (3, 'BND'), (4, 'CPX'), (5, 'CTX'), (6, 'DEL'), (7, 'DUP'), (8, 'INS'), (9, 'INV'), (10, 'CNV')], db_column='svType')),
                ('sv_type_detail', clickhouse_backend.models.Enum8Field(null=True, blank=True, choices=[(1, 'INS_iDEL'), (2, 'INVdel'), (3, 'INVdup'), (4, 'ME'), (5, 'ME:ALU'), (6, 'ME:LINE1'), (7, 'ME:SVA'), (8, 'dDUP'), (9, 'dDUP_iDEL'), (10, 'delINV'), (11, 'delINVdel'), (12, 'delINVdup'), (13, 'dupINV'), (14, 'dupINVdel'), (15, 'dupINVdup')], db_column='svTypeDetail')),
                ('predictions', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('strvctvre', clickhouse_backend.models.DecimalField(blank=True, decimal_places=5, max_digits=9, null=True))])),
                ('populations', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('gnomad_svs', clickhouse_search.backend.fields.NamedTupleField(base_fields=[('af', clickhouse_backend.models.DecimalField(decimal_places=5, max_digits=9)), ('het', clickhouse_backend.models.UInt32Field()), ('hom', clickhouse_backend.models.UInt32Field()), ('id', clickhouse_backend.models.StringField())]))])),
                ('sorted_gene_consequences', clickhouse_search.backend.fields.NestedField(base_fields=[('geneId', clickhouse_backend.models.StringField(blank=True, null=True)), ('majorConsequence', clickhouse_backend.models.Enum8Field(blank=True, choices=[(1, 'LOF'), (2, 'INTRAGENIC_EXON_DUP'), (3, 'PARTIAL_EXON_DUP'), (4, 'COPY_GAIN'), (5, 'DUP_PARTIAL'), (6, 'MSV_EXON_OVERLAP'), (7, 'INV_SPAN'), (8, 'UTR'), (9, 'PROMOTER'), (10, 'TSS_DUP'), (11, 'BREAKEND_EXONIC'), (12, 'INTRONIC'), (13, 'NEAREST_TSS')], null=True))], db_column='sortedTranscriptConsequences')),
            ],
            options={
                'db_table': 'GRCh38/SV/annotations_memory',
                'engine': clickhouse_search.backend.engines.EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SV/annotations', flatten_nested=0, primary_key='key'),
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='EntriesSv',
            fields=[
                ('key', models.ForeignKey(db_column='key', on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='clickhouse_search.annotationssv')),
                ('project_guid', clickhouse_backend.models.StringField(low_cardinality=True)),
                ('family_guid', clickhouse_backend.models.StringField()),
                ('xpos', clickhouse_search.backend.fields.UInt64FieldDeltaCodecField()),
                ('filters', clickhouse_backend.models.ArrayField(base_field=clickhouse_backend.models.StringField(low_cardinality=True))),
                ('calls', clickhouse_backend.models.ArrayField(base_field=clickhouse_search.backend.fields.NamedTupleField(base_fields=[('sampleId', clickhouse_backend.models.StringField()), ('gt', clickhouse_backend.models.Enum8Field(blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')], null=True)), ('cn', clickhouse_backend.models.UInt8Field(blank=True, null=True)), ('gq', clickhouse_backend.models.UInt8Field(blank=True, null=True)), ('newCall', clickhouse_backend.models.BoolField(blank=True, null=True)), ('prevCall', clickhouse_backend.models.BoolField(blank=True, null=True)), ('prevNumAlt', clickhouse_backend.models.Enum8Field(blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')], null=True))]))),
                ('sign', clickhouse_backend.models.Int8Field()),
            ],
            options={
                'db_table': 'GRCh38/SV/entries',
                'abstract': False,
                'engine': clickhouse_search.backend.engines.CollapsingMergeTree('sign', deduplicate_merge_projection_mode='rebuild', index_granularity=8192, order_by=('project_guid', 'family_guid', 'key'), partition_by='project_guid'),
                'projection': clickhouse_search.models.Projection('xpos_projection', order_by='xpos'),
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('_overwrite_base_manager', django.db.models.manager.Manager()),
            ],
        ),
    ]
