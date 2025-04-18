from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from django.db.models.functions import JSONObject

from clickhouse_search.models import EntriesSnvIndel, AnnotationsSnvIndel
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Sample
from settings import CLICKHOUSE_SERVICE_HOSTNAME

def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version, sort=None, page=1, num_results=100, gene_agg=False, **kwargs):
    if genome_version != GENOME_VERSION_GRCh38:
        raise NotImplementedError('Clickhouse search not implemented for genome version other than GRCh38')

    sample_data = _get_sample_data(samples)
    entries = EntriesSnvIndel.objects.filter(
        project_guid=sample_data['project_guid'],
        family_guid=sample_data['family_guid'],
        sample_type=sample_data['sample_type'],
    ).values('gt', 'gq', 'ab', 'dp', 'annotations__variant_id', 'annotations__xpos')[:num_results]
    print(entries)

    return []


def _get_sample_data(samples):
    samples = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
    if not samples:
        raise NotImplementedError('Clickhouse search not implemented for other data types')

    sample_data = samples.values(
        'sample_type', family_guid=F('individual__family__guid'), project_guid=F('individual__family__project__guid'),
    ).annotate(samples=ArrayAgg(JSONObject(affected='individual__affected', sample_id='sample_id')))
    if len(sample_data) > 1:
        raise NotImplementedError('Clickhouse search not implemented for multiple families or sample types')

    return sample_data[0]