import elasticsearch_dsl

from seqr.models import Sample
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS
from seqr.utils.search.utils import get_es_client, get_index_metadata


SAMPLE_FIELDS_LIST = ['samples', 'samples_num_alt_1']
#  support .bgz instead of requiring .vcf.bgz due to issues with DSP delivery of large callsets
DATASET_FILE_EXTENSIONS = VCF_FILE_EXTENSIONS[:-1] + ('.bgz', '.bed', '.mt')


def validate_index_metadata_and_get_samples(elasticsearch_index, **kwargs):
    es_client = get_es_client()

    all_index_metadata = get_index_metadata(elasticsearch_index, es_client, include_fields=True)
    if elasticsearch_index in all_index_metadata:
        index_metadata = all_index_metadata.get(elasticsearch_index)
        _validate_index_metadata(index_metadata, elasticsearch_index, **kwargs)
        sample_field = _get_samples_field(index_metadata)
        sample_type = index_metadata['sampleType']
    else:
        # Aliases return the mapping for all indices in the alias
        metadatas = list(all_index_metadata.values())
        sample_field = _get_samples_field(metadatas[0])
        sample_type = metadatas[0]['sampleType']
        for metadata in metadatas[1:]:
            _validate_index_metadata(metadata, elasticsearch_index, **kwargs)
            if sample_field != _get_samples_field(metadata):
                raise ValueError('Found mismatched sample fields for indices in alias')
            if sample_type != metadata['sampleType']:
                raise ValueError('Found mismatched sample types for indices in alias')

    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field=sample_field, size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets], sample_type


def _get_samples_field(index_metadata):
    return next((field for field in SAMPLE_FIELDS_LIST if field in index_metadata['fields'].keys()))


def _validate_index_metadata(index_metadata, elasticsearch_index, project=None, genome_version=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    metadata_fields = ['genomeVersion', 'sampleType', 'sourceFilePath']
    if any(field not in (index_metadata or {}) for field in metadata_fields):
        raise ValueError("Index metadata must contain fields: {}".format(', '.join(metadata_fields)))

    sample_type = index_metadata['sampleType']
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise ValueError("Sample type not supported: {}".format(sample_type))

    if index_metadata['genomeVersion'] != (genome_version or project.genome_version):
        raise ValueError('Index "{0}" has genome version {1} but this project uses version {2}'.format(
            elasticsearch_index, index_metadata['genomeVersion'], project.genome_version
        ))

    dataset_path = index_metadata['sourceFilePath']
    if not dataset_path.endswith(DATASET_FILE_EXTENSIONS):
        raise ValueError("Variant call dataset path must end with {}".format(' or '.join(DATASET_FILE_EXTENSIONS)))

    if index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS) != dataset_type:
        raise ValueError('Index "{0}" has dataset type {1} but expects {2}'.format(
            elasticsearch_index, index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS), dataset_type
        ))
