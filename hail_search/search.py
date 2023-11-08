from hail_search.queries.multi_data_types import QUERY_CLASS_MAP, SNV_INDEL_DATA_TYPE, MultiDataTypeHailTableQuery


def search_hail_backend(request, gene_counts=False):
    sample_data = request.pop('sample_data', {})
    genome_version = request.pop('genome_version')

    data_types = list(sample_data.keys())
    single_data_type = data_types[0] if len(data_types) == 1 else None

    if single_data_type:
        sample_data = sample_data[single_data_type]
        query_cls = QUERY_CLASS_MAP[single_data_type]
    else:
        query_cls = MultiDataTypeHailTableQuery

    query = query_cls(sample_data, genome_version, **request)
    if gene_counts:
        return query.gene_counts()
    else:
        return query.search()


def lookup_variant(request):
    data_type = request.get('data_type', SNV_INDEL_DATA_TYPE)
    query = QUERY_CLASS_MAP[data_type](sample_data=None, genome_version=request['genome_version'])
    return query.lookup_variant(request['variant_id'])


def load_globals():
    for cls in QUERY_CLASS_MAP.values():
        cls.load_globals()
