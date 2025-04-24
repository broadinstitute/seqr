from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from django.db.models.functions import JSONObject

from clickhouse_search.models import EntriesSnvIndel, AnnotationsSnvIndel
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Sample
from seqr.utils.search.constants import MAX_VARIANTS
from settings import CLICKHOUSE_SERVICE_HOSTNAME

ANNOTATION_VALUES = {
    field.db_column or field.name: F(f'key__{field.name}') for field in AnnotationsSnvIndel._meta.local_fields
    if field.name not in ['key', 'xpos']
}

def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version, sort=None, page=1, num_results=100, gene_agg=False, **kwargs):
    if genome_version != GENOME_VERSION_GRCh38:
        raise NotImplementedError('Clickhouse search not implemented for genome version other than GRCh38')

    sample_data = _get_sample_data(samples)
    entries = _get_filtered_family_entries(sample_data)
    # TODO Subquery with OuterRef
    # results = entries.values('gt', 'gq', 'ab', 'dp', 'xpos', **ANNOTATION_VALUES)
    from django.db.models import Subquery, OuterRef
    results = AnnotationsSnvIndel.objects.annotate(
        entries=Subquery(entries.values('calls'))
    ).values('variant_id', 'entries')
    results = results[:5]
    # results = results[:MAX_VARIANTS+1]
    print(results)

    previous_search_results.update({
        'total_results': len(results),
        'all_results': results,
    })

    return results[(page-1)*num_results:page*num_results]


def _get_filtered_family_entries(sample_data):
    if len(sample_data) > 1:
        raise NotImplementedError('Clickhouse search not implemented for multiple families or sample types')

    return EntriesSnvIndel.objects.filter(
        project_guid=sample_data[0]['project_guid'],
        family_guid=sample_data[0]['family_guid'],
        sample_type=sample_data[0]['sample_type'],
    )


def _get_sample_data(samples):
    samples = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
    if not samples:
        raise NotImplementedError('Clickhouse search not implemented for other data types')

    return samples.values(
        'sample_type', family_guid=F('individual__family__guid'), project_guid=F('individual__family__project__guid'),
    ).annotate(samples=ArrayAgg(JSONObject(affected='individual__affected', sample_id='sample_id')))