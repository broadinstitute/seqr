from seqr.utils.search.elasticsearch.es_utils import validate_index_metadata_and_get_samples


def get_valid_search_samples(data_source, **kwargs):
    return validate_index_metadata_and_get_samples(data_source, **kwargs)