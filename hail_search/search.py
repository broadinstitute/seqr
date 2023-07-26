from hail_search.hail_search_query import QUERY_CLASS_MAP


def search_hail_backend(request):
    sample_data = request.pop('sample_data', {})

    data_types = list(sample_data.keys())
    single_data_type = data_types[0] if len(data_types) == 1 else None

    sample_data = sample_data[single_data_type]
    data_type = single_data_type
    query_cls = QUERY_CLASS_MAP[single_data_type]

    query = query_cls(data_type, sample_data=sample_data, **request)
    return query.search()
