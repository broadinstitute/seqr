from hail_search.constants import SV_DATASET
from hail_search.hail_search_query import AllSvHailTableQuery, AllVariantHailTableQuery, AllDataTypeHailTableQuery, \
    QUERY_CLASS_MAP


def search_hail_backend(request):
    sample_data = request.pop('sample_data', {})

    data_types = list(sample_data.keys())
    single_data_type = data_types[0] if len(data_types) == 1 else None

    if single_data_type:
        sample_data = sample_data[single_data_type]
        data_type = single_data_type
        query_cls = QUERY_CLASS_MAP[single_data_type]
    else:
        sample_data = {k: v for k, v in sample_data.items() if k in data_types}
        data_type = data_types
        is_all_svs = all(dt.startswith(SV_DATASET) for dt in data_types)
        is_no_sv = all(not dt.startswith(SV_DATASET) for dt in data_types)

        if is_all_svs:
            query_cls = AllSvHailTableQuery
        elif is_no_sv:
            query_cls = AllVariantHailTableQuery
        else:
            query_cls = AllDataTypeHailTableQuery

    return query_cls(data_type, sample_data=sample_data, **request).search()
