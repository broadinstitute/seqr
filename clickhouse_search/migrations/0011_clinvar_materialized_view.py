# Generated manually by the seqr team.
from string import Template

from django.db import migrations


CLINVAR_ALL_VARIANTS_TO_CLINVAR = Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/clinvar_all_variants_to_clinvar`
REFRESH EVERY 10 YEAR
TO `$reference_genome/$dataset_type/clinvar`
AS 
SELECT
    DISTINCT ON (key)
    kl.key as key, 
    alleleId,
    conflictingPathogenicities,
    goldStars,
    submitters,
    conditions,
    assertions,
    pathogenicity
FROM `$reference_genome/$dataset_type/clinvar_all_variants` c
INNER JOIN `$reference_genome/$dataset_type/key_lookup` kl
ON c.variantId = kl.variantId
""")

class Migration(migrations.Migration):

    dependencies = [
        ('clickhouse_search', '0010_clinvarallvariantsgrch37snvindel_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            CLINVAR_ALL_VARIANTS_TO_CLINVAR.substitute(
                reference_genome='GRCh37',
                dataset_type='SNV_INDEL',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            CLINVAR_ALL_VARIANTS_TO_CLINVAR.substitute(
                reference_genome='GRCh38',
                dataset_type='SNV_INDEL',
            ),
            hints={'clickhouse': True},
        ),
        migrations.RunSQL(
            CLINVAR_ALL_VARIANTS_TO_CLINVAR.substitute(
                reference_genome='GRCh38',
                dataset_type='MITO',
            ),
            hints={'clickhouse': True},
        ),
    ]

