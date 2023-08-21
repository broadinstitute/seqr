from hail_search.hail_search_query import QUERY_CLASS_MAP


def search_hail_backend(request, gene_counts=False):
    sample_data = request.pop('sample_data', {})
    genome_version = request.pop('genome_version')

    data_types = list(sample_data.keys())
    single_data_type = data_types[0] if len(data_types) == 1 else None

    sample_data = sample_data[single_data_type]
    query_cls = QUERY_CLASS_MAP[single_data_type]

    query = query_cls(sample_data, genome_version, **request)
    if gene_counts:
        return query.gene_counts()
    else:
        return query.search()


def load_globals():
    for cls in QUERY_CLASS_MAP.values():
        cls.load_globals()
