from hail_search.hail_search_query import QUERY_CLASS_MAP


def search_hail_backend(request, all_globals):
    sample_data = request.pop('sample_data', {})
    genome_version = request.pop('genome_version')

    data_types = list(sample_data.keys())
    single_data_type = data_types[0] if len(data_types) == 1 else None

    sample_data = sample_data[single_data_type]
    query_cls = QUERY_CLASS_MAP[single_data_type]
    data_type_globals = all_globals[single_data_type][genome_version]

    query = query_cls(sample_data, genome_version, data_type_globals, **request)
    return query.search()


def load_globals():
    return {k: cls.load_globals() for k, cls in QUERY_CLASS_MAP.items()}
