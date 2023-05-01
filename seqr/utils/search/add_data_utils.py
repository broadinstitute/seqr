from seqr.models import Sample
from seqr.utils.search.elasticsearch.es_utils import validate_index_metadata_and_get_samples


def get_search_sample_queryset(projects):
    return Sample.objects.filter(
        individual__family__project__in=projects, is_active=True, elasticsearch_index__isnull=False,
    )


def get_valid_search_samples(data_source, **kwargs):
    return validate_index_metadata_and_get_samples(data_source, **kwargs)
