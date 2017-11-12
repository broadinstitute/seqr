from django.core.exceptions import ObjectDoesNotExist


def get_elasticsearch_dataset(project_id, family_id=None):
    """Returns the VariantDataset that contains variant data for the given project and family, or
    None if this data hasn't been loaded into elasticsearch.
    """

    from seqr.models import VariantsDataset

    if family_id is None:
        # return the index for this project
        variant_dataset = VariantsDataset.objects.filter(
            analysis_type = VariantsDataset.ANALYSIS_TYPE_VARIANT_CALLS,
            is_loaded = True,
            elasticsearch_index__isnull=False,
            project__deprecated_project_id=project_id,
        )
        if not variant_dataset:
            return None

        # in case this project has so many samples that the data is split across multiple
        # indices, just return the first one.
        return list(variant_dataset)[0]


    try:
        variant_dataset = VariantsDataset.objects.get(
            analysis_type = VariantsDataset.ANALYSIS_TYPE_VARIANT_CALLS,
            is_loaded = True,
            elasticsearch_index__isnull=False,
            project__deprecated_project_id=project_id,
            sample__individual__family__family_id=family_id,
        )
        return variant_dataset

    except ObjectDoesNotExist as e:
        return None

