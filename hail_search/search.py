from hail_search.constants import VARIANT_DATASET, SV_DATASET, MITO_DATASET, SCREEN_KEY, NEW_SV_FIELD, \
    SV_ANNOTATION_TYPES, QUERY_CLASS_MAP
from hail_search.hail_search_query import AllSvHailTableQuery, AllVariantHailTableQuery, AllDataTypeHailTableQuery


def _search_data_type(variant_ids=None, annotations=None, annotations_secondary=None, **kwargs):
    if variant_ids:
        return VARIANT_DATASET

    annotation_types = {k for k, v in annotations.items() if v}
    if annotations_secondary:
        annotation_types.update({k for k, v in annotations_secondary.items() if v})

    if SCREEN_KEY not in annotation_types and (
            NEW_SV_FIELD in annotation_types or annotation_types.issubset(SV_ANNOTATION_TYPES)):
        return SV_DATASET
    elif annotation_types.isdisjoint(SV_ANNOTATION_TYPES):
        return VARIANT_DATASET
    return None


def search_hail_backend(request):
    sample_data = request.pop('sample_data', {})

    data_type = _search_data_type(**request)
    data_types = list(sample_data.keys())

    if data_type == VARIANT_DATASET:
        data_types = [
            dt for dt in data_types if dt in {VARIANT_DATASET, MITO_DATASET}
        ]
    elif data_type == SV_DATASET:
        data_types = [dt for dt in data_types if dt.startswith(SV_DATASET)]

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
