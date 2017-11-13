from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger()

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
            elasticsearch_host__isnull=False,
            project__deprecated_project_id=project_id,
        ).distinct()
        
        if not elasticsearch_dataset:
            return None

        # in case this project has so many samples that the data is split across multiple
        # indices, just return the first one.
        return list(elasticsearch_dataset)[0]

    elasticsearch_dataset = ElasticsearchDataset.objects.filter(
        analysis_type = ElasticsearchDataset.ANALYSIS_TYPE_VARIANT_CALLS,
        is_loaded = True,
        elasticsearch_host__isnull=False,
        project__deprecated_project_id=project_id,
        samples__individual__family__family_id=family_id,
    ).distinct()

    logger.info("Getting dataset for %s family %s: %s" % (project_id, family_id, elasticsearch_dataset))
                
    if not elasticsearch_dataset:
        return None
    
    return list(elasticsearch_dataset)[0]


