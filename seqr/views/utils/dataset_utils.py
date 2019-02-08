import logging
import elasticsearch_dsl
from elasticsearch import NotFoundError, TransportError
from django.utils import timezone
from collections import defaultdict

from seqr.views.apis.igv_api import proxy_to_igv
from seqr.models import Sample, Individual
from seqr.utils.es_utils import get_es_client, VARIANT_DOC_TYPE
from seqr.utils.file_utils import does_file_exist, file_iter, get_file_stats
from seqr.views.utils.file_utils import load_uploaded_file, parse_file
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records

logger = logging.getLogger(__name__)


def add_dataset(
    project,
    sample_type,
    dataset_type,
    elasticsearch_index=None,
    dataset_path=None,
    dataset_name=None,
    max_edit_distance=0,
    mapping_file_path=None,
    mapping_file_id=None,
    ignore_missing_family_members=False,
    ignore_extra_samples_in_callset=False
):

    """Validates the given dataset and updates/ creates the corresponding Samples

    Args:
        project (object):
        sample_type (string):
        dataset_type (string):
        dataset_name (string):
        dataset_path (string):
        max_edit_distance (int):
        elasticsearch_index (string):
        mapping_file_path (string):
        mapping_file_id (string):
        ignore_extra_samples_in_callset (bool):
    Return:
        (updated_sample_models, created_sample_ids) tuple
    """

    _validate_inputs(
        dataset_type=dataset_type, sample_type=sample_type, dataset_path=dataset_path, project=project,
        elasticsearch_index=elasticsearch_index, mapping_file_id=mapping_file_id
    )

    update_kwargs = {
        'project': project,
        'sample_type': sample_type,
        'dataset_type': dataset_type,
        'elasticsearch_index': elasticsearch_index,
        'dataset_name': dataset_name,
        'max_edit_distance': max_edit_distance,
        'ignore_extra_samples_in_callset': ignore_extra_samples_in_callset,
        'ignore_missing_family_members': ignore_missing_family_members,
    }

    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        all_samples = _get_elasticsearch_index_samples(elasticsearch_index, project)
        update_kwargs.update({
            'sample_ids': all_samples,
            'sample_id_to_individual_id_mapping': _load_mapping_file(mapping_file_id, mapping_file_path),
            'sample_dataset_path_mapping': {sample_id: dataset_path for sample_id in all_samples},
            'missing_sample_exception_template': 'Matches not found for ES sample ids: {unmatched_samples}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'
        })

    elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
        sample_id_to_individual_id_mapping = {}
        sample_dataset_path_mapping = {}
        errors = []
        for individual_id, dataset_path in _load_mapping_file(mapping_file_id, mapping_file_path).items():
            if not (dataset_path.endswith(".bam") or dataset_path.endswith(".cram")):
                raise Exception('BAM / CRAM file "{}" must have a .bam or .cram extension'.format(dataset_path))
            _validate_alignment_dataset_path(dataset_path)
            sample_id = dataset_path.split('/')[-1].split('.')[0]
            sample_id_to_individual_id_mapping[sample_id] = individual_id
            sample_dataset_path_mapping[sample_id] = dataset_path

        if errors:
            raise Exception(', '.join(errors))

        update_kwargs.update({
            'sample_ids': sample_id_to_individual_id_mapping.keys(),
            'sample_id_to_individual_id_mapping': sample_id_to_individual_id_mapping,
            'sample_dataset_path_mapping': sample_dataset_path_mapping,
            'ignore_missing_family_members': True,
            'missing_sample_exception_template': 'The following Individual IDs do not exist: {unmatched_samples}'
        })

    return _update_samples_for_dataset(**update_kwargs)


def _update_samples_for_dataset(
    project,
    sample_ids,
    sample_type,
    dataset_type,
    elasticsearch_index=None,
    dataset_name=None,
    max_edit_distance=0,
    sample_id_to_individual_id_mapping=None,
    sample_dataset_path_mapping=None,
    ignore_extra_samples_in_callset=False,
    ignore_missing_family_members=False,
    missing_sample_exception_template='Missing samples: {unmatched_samples}',
):
    matched_sample_id_to_sample_record, created_sample_ids = match_sample_ids_to_sample_records(
        project=project,
        sample_ids=sample_ids,
        sample_type=sample_type,
        dataset_type=dataset_type,
        elasticsearch_index=elasticsearch_index,
        max_edit_distance=max_edit_distance,
        create_sample_records=True,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
    )

    unmatched_samples = set(sample_ids) - set(matched_sample_id_to_sample_record.keys())
    if not ignore_extra_samples_in_callset and len(unmatched_samples) > 0:
        raise Exception(missing_sample_exception_template.format(unmatched_samples=", ".join(unmatched_samples)))

    if ignore_extra_samples_in_callset and len(matched_sample_id_to_sample_record) == 0:
        raise Exception("None of the individuals or samples in the project matched the {} expected sample id(s)".format(
            len(sample_ids)
        ))

    if not ignore_missing_family_members:
        included_family_individuals = defaultdict(set)
        for sample in matched_sample_id_to_sample_record.values():
            included_family_individuals[sample.individual.family].add(sample.individual.individual_id)
        missing_family_individuals = []
        for family, individual_ids in included_family_individuals.items():
            missing_indivs = family.individual_set.exclude(individual_id__in=individual_ids)
            if missing_indivs:
                missing_family_individuals.append(
                    '{} ({})'.format(family.family_id, ', '.join([i.individual_id for i in missing_indivs]))
                )
        if missing_family_individuals:
            raise Exception(
                'The following families are included in the callset but are missing some family members: {}. This can lead to errors in variant search. If you still want to upload this callset, select the "Ignore missing family members" checkbox.'.format(
                    ', '.join(missing_family_individuals)
                ))

    not_loaded_samples = []
    update_json = {}
    loaded_date = timezone.now()
    if dataset_name:
        update_json['dataset_name'] = dataset_name
    if elasticsearch_index:
        update_json['elasticsearch_index'] = elasticsearch_index
    for sample_id, sample in matched_sample_id_to_sample_record.items():
        sample_update_json = {}
        if sample_dataset_path_mapping and sample_dataset_path_mapping.get(sample_id):
            sample_update_json['dataset_file_path'] = sample_dataset_path_mapping[sample_id]
        if sample.sample_status != Sample.SAMPLE_STATUS_LOADED:
            not_loaded_samples.append(sample_id)
            sample_update_json['sample_status'] = Sample.SAMPLE_STATUS_LOADED
            sample_update_json['loaded_date'] = loaded_date
        sample_update_json.update(update_json)
        update_model_from_json(sample, sample_update_json)

    return matched_sample_id_to_sample_record.values(), created_sample_ids


def _get_elasticsearch_index_samples(elasticsearch_index, project):
    sample_field_suffix = '_num_alt'

    es_client = get_es_client(timeout=30)
    index = elasticsearch_dsl.Index('{}*'.format(elasticsearch_index), using=es_client)
    try:
        field_mapping = index.get_field_mapping(fields=['*{}'.format(sample_field_suffix), 'join_field'], doc_type=[VARIANT_DOC_TYPE])
    except NotFoundError:
        raise Exception('Index "{}" not found'.format(elasticsearch_index))
    except TransportError as e:
        raise Exception(e.error)

    #  Nested genotypes
    if field_mapping.get(elasticsearch_index, {}).get('mappings', {}).get(VARIANT_DOC_TYPE, {}).get('join_field'):
        max_samples = Individual.objects.filter(family__project=project).count()
        s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
        s = s.params(size=0)
        s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field='sample_id', size=max_samples))
        response = s.execute()
        return [agg['key'] for agg in response.aggregations.sample_ids.buckets]

    samples = set()
    for index in field_mapping.values():
        samples.update([key.split(sample_field_suffix)[0] for key in index.get('mappings', {}).get(VARIANT_DOC_TYPE, {}).keys()])
    if not samples:
        raise Exception('No sample fields found for index "{}"'.format(elasticsearch_index))
    return samples


def _validate_inputs(dataset_type, sample_type, dataset_path, project, elasticsearch_index, mapping_file_id):
    # basic sample type checks
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise Exception("Sample type not supported: {}".format(sample_type))

    # datatset_type-specific checks
    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        validate_variant_call_inputs(sample_type, dataset_path, project, elasticsearch_index)

    elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
        if not mapping_file_id:
            raise Exception('Mapping file is required')
    else:
        raise Exception("Dataset type not supported: {}".format(dataset_type))


def validate_variant_call_inputs(sample_type, dataset_path, project, elasticsearch_index):
    if not elasticsearch_index:
        raise Exception('Elasticsearch index is required')
    parsed_es_index = elasticsearch_index.lower().split('__')
    if len(parsed_es_index) > 1:
        if sample_type.lower() not in parsed_es_index:
            raise Exception('Index "{0}" is not associated with sample type "{1}"'.format(
                elasticsearch_index, sample_type
            ))
        genome_version = next((s for s in parsed_es_index if s.startswith('grch')), '').lstrip('grch')
        if genome_version and genome_version != project.genome_version:
            raise Exception('Index "{0}" has genome version {1} but this project uses version {2}'.format(
                elasticsearch_index, genome_version, project.genome_version
            ))

    if dataset_path:
        if not dataset_path.endswith(".vcf.gz") and not dataset_path.endswith(".vds"):
            raise Exception("Variant call dataset path must end with .vcf.gz or .vds")

        # TODO need to fix credentials
        #_validate_dataset_path(dataset_path)
        #_validate_vcf(dataset_path)


def _validate_alignment_dataset_path(dataset_path):
    headers = {'Range': 'bytes=0-100'} if dataset_path.endswith('.bam') else {}
    resp = proxy_to_igv(dataset_path, {'options': '-b,-H'}, method='GET', scheme='http', headers=headers)
    if resp.status_code >= 400 or (resp.get('Content-Type') != 'application/octet-stream' and resp.get('Content-Encoding') != 'gzip'):
        raise Exception('Error accessing "{}": {}'.format(dataset_path, resp.content))


def _validate_dataset_path(dataset_path):
    try:
        dataset_file = does_file_exist(dataset_path)
        if dataset_file is None:
            raise Exception('"{}" not found'.format(dataset_path))
        # check that dataset_path is accessible
        dataset_file_stats = get_file_stats(dataset_path)
        if dataset_file_stats is None:
            raise Exception('Unable to access "{}"'.format(dataset_path))
    except Exception as e:
        raise Exception("Dataset path error: " + str(e))


def _validate_vcf(vcf_path):
    header_line = None
    for line in file_iter(vcf_path):
        if line.startswith("#CHROM"):
            header_line = line
            break
        if line.startswith("#"):
            continue
        else:
            break

    if not header_line:
        raise Exception("Unexpected VCF header. #CHROM not found before line: {}".format(line))

    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    if not sample_ids:
        raise Exception('No samples found in VCF "{}"'.format(vcf_path))


def _load_mapping_file(mapping_file_id, mapping_file_path):
    id_mapping = {}
    file_content = []
    if mapping_file_id:
        file_content = load_uploaded_file(mapping_file_id)
    elif mapping_file_path:
        file_content = parse_file(mapping_file_path, file_iter(mapping_file_path))
    for line in file_content:
        if len(line) != 2:
            raise ValueError("Must contain 2 columns: " + ', '.join(line))
        id_mapping[line[0]] = line[1]
    return id_mapping
