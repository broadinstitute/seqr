from django.core.exceptions import ObjectDoesNotExist


def get_elasticsearch_dataset(project_id, family_id=None):
    """Returns the VariantDataset that contains variant data for the given project and family, or
    None if this data hasn't been loaded into elasticsearch.
    """

    from seqr.models import ElasticsearchDataset

    if family_id is None:
        # return the index for this project
        elasticsearch_dataset = ElasticsearchDataset.objects.filter(
            analysis_type = ElasticsearchDataset.ANALYSIS_TYPE_VARIANT_CALLS,
            is_loaded = True,
            elasticsearch_index__isnull=False,
            project__deprecated_project_id=project_id,
        )
        if not elasticsearch_dataset:
            return None

        # in case this project has so many samples that the data is split across multiple
        # indices, just return the first one.
        return list(elasticsearch_dataset)[0]


    try:
        elasticsearch_dataset = ElasticsearchDataset.objects.get(
            analysis_type = ElasticsearchDataset.ANALYSIS_TYPE_VARIANT_CALLS,
            is_loaded = True,
            elasticsearch_index__isnull=False,
            project__deprecated_project_id=project_id,
            samples__individual__family__family_id=family_id,
        )
        return elasticsearch_dataset

    except ObjectDoesNotExist as e:
        return None

