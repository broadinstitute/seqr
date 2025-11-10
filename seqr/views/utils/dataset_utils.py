from collections import defaultdict
from datetime import datetime
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Q
from django.utils import timezone
import gzip
import json
import os
from tqdm import tqdm

from seqr.models import Sample, Individual, Family, Project, RnaSample, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier
from seqr.utils.file_utils import file_iter
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.add_data_utils import basic_notify_search_data_loaded
from seqr.utils.xpos_utils import format_chrom
from seqr.views.utils.file_utils import parse_file, get_temp_file_path, persist_temp_file
from seqr.views.utils.json_utils import _to_snake_case, _to_camel_case
from seqr.views.utils.permissions_utils import is_internal_anvil_project, project_has_anvil
from reference_data.models import GeneInfo

logger = SeqrLogger(__name__)


def load_mapping_file(mapping_file_path, user):
    file_content = parse_file(mapping_file_path, file_iter(mapping_file_path, user=user))
    return load_mapping_file_content(file_content)


def load_mapping_file_content(file_content):
    id_mapping = {}
    for line in file_content:
        if len(line) != 2:
            raise ValueError("Must contain 2 columns: " + ', '.join(line))
        id_mapping[line[0]] = line[1]
    return id_mapping


def _find_or_create_samples(
        sample_project_tuples,
        projects,
        user,
        sample_type,
        dataset_type,
        sample_id_to_individual_id_mapping,
        raise_no_match_error=False,
        raise_unmatched_error_template=None,
        sample_data=None,
):
    sample_params = {'sample_type': sample_type, 'dataset_type': dataset_type}
    sample_params.update(sample_data or {})

    samples_by_key = {
        (s.pop('sample_id'), s.pop('individual__family__project__name')): s
        for s in Sample.objects.filter(
            individual__family__project__in=projects,
            sample_id__in={sample_id for sample_id, _ in sample_project_tuples},
            **sample_params
        ).values('guid', 'individual_id', 'sample_id', 'individual__family__project__name')
    }
    existing_samples = {
        key: s for key, s in samples_by_key.items() if key in sample_project_tuples
    }
    remaining_sample_keys = set(sample_project_tuples) - set(existing_samples.keys())

    matched_individual_ids = {sample['individual_id'] for sample in existing_samples.values()}
    loaded_date = timezone.now()
    samples_guids = [sample['guid'] for sample in existing_samples.values()]
    individual_ids = {sample['individual_id'] for sample in existing_samples.values()}
    if len(remaining_sample_keys) > 0:
        remaining_individuals_dict = _get_individuals_by_key(projects, matched_individual_ids)

        # find Individual records with exactly-matching individual_ids
        sample_id_to_individual_record = {}
        for sample_key in remaining_sample_keys:
            individual_key = _get_individual_key(sample_key, sample_id_to_individual_id_mapping)
            if individual_key not in remaining_individuals_dict:
                continue
            sample_id_to_individual_record[sample_key] = remaining_individuals_dict[individual_key]
            del remaining_individuals_dict[individual_key]

        logger.debug(str(len(sample_id_to_individual_record)) + " matched individual ids", user)

        remaining_sample_keys -= set(sample_id_to_individual_record.keys())
        if raise_no_match_error and len(remaining_sample_keys) == len(sample_project_tuples):
            raise ValueError(
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(len(sample_project_tuples)))
        if raise_unmatched_error_template and remaining_sample_keys:
            raise ValueError(raise_unmatched_error_template.format(
                sample_ids=(', '.join(sorted([sample_id for sample_id, _ in remaining_sample_keys])))))

        # create new Sample records for Individual records that matches
        new_sample_args = {
            sample_key: {
                'individual_id': individual['id'],
                'sample_id': sample_key[0],
            } for sample_key, individual in sample_id_to_individual_record.items()
        }
        individual_ids.update({sample['individual_id'] for sample in new_sample_args.values()})
        new_sample_models = _create_samples(
            new_sample_args.values(),
            user,
            loaded_date=loaded_date,
            **sample_params,
        )
        samples_guids += [s.guid for s in new_sample_models]

    return samples_guids, individual_ids, loaded_date


def _create_samples(sample_data, user, loaded_date=timezone.now(), **kwargs):
    new_samples = [
        Sample(
            loaded_date=loaded_date,
            **created_sample_data,
            **kwargs,
        ) for created_sample_data in sample_data]
    return Sample.bulk_create(user, new_samples)


def _create_rna_samples(sample_data, sample_guid_ids_to_load, user, **kwargs):
    new_samples = [RnaSample(**sample, **kwargs) for sample in sample_data]
    new_sample_models = RnaSample.bulk_create(user, new_samples)
    new_sample_ids = [s.id for s in new_sample_models]
    sample_guid_ids_to_load.update(
        dict(RnaSample.objects.filter(id__in=new_sample_ids).values_list('guid', 'individual__individual_id'))
    )


def _get_rna_sample_data_by_key(values=None, **kwargs):
    key_fields = ['individual_id', 'tissue_type']
    return {
        tuple(s.pop(k) for k in key_fields): s
        for s in RnaSample.objects.filter(**kwargs).values('guid', *key_fields, **(values or {}))
    }


def _get_individuals_by_key(projects, matched_individual_ids=None):
    individuals = Individual.objects.filter(family__project__in=projects)
    if matched_individual_ids:
        individuals = individuals.exclude(id__in=matched_individual_ids)
    return {
        (i['individual_id'], i.pop('family__project__name')): i
        for i in individuals.values('id', 'individual_id', 'family__project__name')
    }


def _get_individual_key(sample_key, sample_id_to_individual_id_mapping):
    return ((sample_id_to_individual_id_mapping or {}).get(sample_key[0], sample_key[0]), sample_key[1])


def _validate_samples_families(samples_guids, included_family_guids, sample_type, dataset_type, expected_families=None):
    missing_individuals = Individual.objects.filter(
        family__guid__in=included_family_guids,
        sample__is_active=True,
        sample__dataset_type=dataset_type,
        sample__sample_type=sample_type,
    ).exclude(sample__guid__in=samples_guids).select_related('family')
    missing_family_individuals = defaultdict(list)
    for individual in missing_individuals:
        missing_family_individuals[individual.family].append(individual)

    if missing_family_individuals:
        raise ValueError(
            'The following families are included in the callset but are missing some family members: {}.'.format(
                ', '.join(sorted(
                    ['{} ({})'.format(family.family_id, ', '.join(sorted([i.individual_id for i in missing_indivs])))
                     for family, missing_indivs in missing_family_individuals.items()]
                ))))

    if expected_families:
        missing_families = [f.family_id for f in expected_families if f.guid not in included_family_guids]
        if missing_families:
            raise ValueError(
                'The following families have saved variants but are missing from the callset: {}.'.format(
                    ', '.join(missing_families)
                ))


def _update_variant_samples(samples_guids, individual_ids, user, dataset_type, sample_type, sample_data):

    activated_sample_guids = Sample.bulk_update(user, {
        'is_active': True,
        **sample_data,
    }, guid__in=samples_guids, is_active=False)

    inactivate_samples = Sample.objects.filter(
        individual_id__in=individual_ids,
        is_active=True,
        dataset_type=dataset_type,
        sample_type=sample_type,
    ).exclude(guid__in=samples_guids)

    inactivate_sample_guids = Sample.bulk_update(user, {'is_active': False}, queryset=inactivate_samples)

    return activated_sample_guids, inactivate_sample_guids


def match_and_update_search_samples(
        projects, sample_project_tuples, sample_type, dataset_type, sample_data, user, expected_families=None,
        sample_id_to_individual_id_mapping=None, raise_unmatched_error_template='Matches not found for sample ids: {sample_ids}',
):
    samples_guids, individual_ids, loaded_date = _find_or_create_samples(
        sample_project_tuples=sample_project_tuples,
        projects=projects,
        user=user,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_no_match_error=not raise_unmatched_error_template,
        raise_unmatched_error_template=raise_unmatched_error_template,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_data=sample_data,
    )

    included_families = dict(Family.objects.filter(individual__id__in=individual_ids).values_list('guid', 'analysis_status'))
    _validate_samples_families(samples_guids, included_families.keys(), sample_type, dataset_type, expected_families=expected_families)

    activated_sample_guids, inactivated_sample_guids = _update_variant_samples(
        samples_guids, individual_ids, user, dataset_type, sample_type, sample_data={'loaded_date': loaded_date, **sample_data})
    updated_samples = Sample.objects.filter(guid__in=activated_sample_guids)

    family_guids_to_update = [
        family_guid for family_guid, analysis_status in included_families.items()
        if analysis_status in {Family.ANALYSIS_STATUS_WAITING_FOR_DATA, Family.ANALYSIS_STATUS_LOADING_FAILED}
    ]
    Family.bulk_update(
        user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    previous_loaded_individuals = set(Sample.objects.filter(guid__in=inactivated_sample_guids).values_list('individual_id', flat=True))
    new_samples = updated_samples.exclude(individual_id__in=previous_loaded_individuals)

    return new_samples, updated_samples, inactivated_sample_guids, family_guids_to_update


def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]


SAMPLE_ID_COL = 'sample_id'
SAMPLE_ID_HEADER_COL = 'sampleID'
GENE_ID_COL = 'gene_id'
GENE_ID_HEADER_COL = 'geneID'
RNA_OUTLIER_COLUMNS = {GENE_ID_HEADER_COL: GENE_ID_COL, 'pValue': 'p_value', 'padjust': 'p_adjust', 'zScore': 'z_score',
                       SAMPLE_ID_HEADER_COL: SAMPLE_ID_COL}

TPM_COL = 'TPM'
TPM_HEADER_COLS = {
    SAMPLE_ID_COL: SAMPLE_ID_COL, GENE_ID_COL: GENE_ID_COL, 'Name': GENE_ID_COL, TPM_COL: TPM_COL.lower(),
}

CHROM_COL = 'chrom'
START_COL = 'start'
END_COL = 'end'
STRAND_COL = 'strand'
COUNTS_COL = 'counts'
MEAN_COUNTS_COL = 'mean_counts'
TOTAL_COUNTS_COL = 'total_counts'
MEAN_TITAL_COUNTS_COL = 'mean_total_counts'
SPLICE_TYPE_COL = 'type'
P_VALUE_COL ='p_value'
P_ADJUST_COL ='p_adjust'
DELTA_INDEX_COL = 'delta_intron_jaccard_index'
RARE_DISEASE_SAMPLES_WITH_JUNCTION = 'rare_disease_samples_with_this_junction'
RARE_DISEASE_SAMPLES_TOTAL = 'rare_disease_samples_total'
SPLICE_OUTLIER_COLS = [
    CHROM_COL, START_COL, END_COL, STRAND_COL, SPLICE_TYPE_COL, P_VALUE_COL, P_ADJUST_COL, DELTA_INDEX_COL, COUNTS_COL,
    MEAN_COUNTS_COL, TOTAL_COUNTS_COL, MEAN_TITAL_COUNTS_COL, RARE_DISEASE_SAMPLES_WITH_JUNCTION,
    RARE_DISEASE_SAMPLES_TOTAL,
]
SPLICE_OUTLIER_FORMATTER = {
    CHROM_COL: format_chrom,
    START_COL: int,
    END_COL: int,
    COUNTS_COL: int,
    MEAN_COUNTS_COL: float,
    TOTAL_COUNTS_COL: int,
    MEAN_TITAL_COUNTS_COL: float,
    RARE_DISEASE_SAMPLES_WITH_JUNCTION: int,
    RARE_DISEASE_SAMPLES_TOTAL: int,
    P_VALUE_COL: float,
    P_ADJUST_COL: float,
    DELTA_INDEX_COL: float,
}

SPLICE_OUTLIER_HEADER_COLS = {_to_camel_case(col): col for col in SPLICE_OUTLIER_COLS}
SPLICE_OUTLIER_HEADER_COLS.update({
    SAMPLE_ID_HEADER_COL: SAMPLE_ID_COL, GENE_ID_HEADER_COL: GENE_ID_COL, 'hgncSymbol': GENE_ID_COL,
    'seqnames': CHROM_COL, 'padjust': P_ADJUST_COL, 'deltaPsi': DELTA_INDEX_COL,
})


def _get_splice_id(row):
    return '-'.join([row[GENE_ID_COL], row[CHROM_COL], str(row[START_COL]), str(row[END_COL]), row[STRAND_COL],
                    row[SPLICE_TYPE_COL]])


RNA_DATA_TYPE_CONFIGS = {
    RnaSample.DATA_TYPE_EXPRESSION_OUTLIER: {
        'model_class': RnaSeqOutlier,
        'columns': RNA_OUTLIER_COLUMNS,
        'additional_kwargs': {},
    },
    RnaSample.DATA_TYPE_TPM: {
        'model_class': RnaSeqTpm,
        'columns': TPM_HEADER_COLS,
        'additional_kwargs': {'sample_id_header_col_config': (TPM_COL.lower(), {'Description'})},
    },
    RnaSample.DATA_TYPE_SPLICE_OUTLIER: {
        'model_class': RnaSeqSpliceOutlier,
        'columns': SPLICE_OUTLIER_HEADER_COLS,
        'additional_kwargs': {
            'allow_missing_gene': True,
            'optional_columns': {RARE_DISEASE_SAMPLES_WITH_JUNCTION, RARE_DISEASE_SAMPLES_TOTAL},
        },
        'post_process_kwargs': {
            'get_unique_key': _get_splice_id,
            'format_fields': SPLICE_OUTLIER_FORMATTER,
        },
    },
}


def _validate_rna_header(header, allowed_column_map, optional_columns, sample_id_header_col_config):
    expected_cols = set(allowed_column_map.values()) - set(optional_columns or [])
    column_map = {allowed_column_map[col]: col for col in header if col in allowed_column_map}
    missing_cols = expected_cols - set(column_map.keys())

    file_sample_id = None
    if SAMPLE_ID_COL in missing_cols and sample_id_header_col_config:
        sample_id_col, other_cols = sample_id_header_col_config
        if sample_id_col in missing_cols:
            file_sample_id = next((col for col in header if col not in allowed_column_map and col not in other_cols), None)
            if file_sample_id:
                column_map[sample_id_col] = file_sample_id
                missing_cols -= {SAMPLE_ID_COL, sample_id_col}

    if missing_cols:
        mapped_missing = defaultdict(list)
        for col, mapped_col in allowed_column_map.items():
            if mapped_col in missing_cols:
                mapped_missing[mapped_col].append(col)
        missing_summary = [cols[0] if len(cols) == 1 else ' OR '.join(sorted(cols)) for cols in mapped_missing.values()]
        raise ValueError(f'Invalid file: missing column(s): {", ".join(sorted(missing_summary))}')

    return file_sample_id, column_map


def _load_rna_seq_file(
        file_path, data_source, user, data_type, model_cls, potential_samples, sample_files, file_dir, individual_data_by_id,
        allowed_column_map, allow_missing_gene=False, ignore_extra_samples=False, optional_columns=None, sample_id_header_col_config=None,
):
    f = file_iter(file_path, user=user)
    parsed_f = parse_file(file_path.replace('.gz', ''), f, iter_file=True)
    header = next(parsed_f)
    file_sample_id, column_map = _validate_rna_header(header, allowed_column_map, optional_columns, sample_id_header_col_config)

    loaded_samples = set()
    unmatched_samples = set()
    samples_to_create = {}
    sample_guid_ids_to_load = {}
    missing_required_fields = defaultdict(set)
    gene_ids = set()
    for line in tqdm(parsed_f, unit=' rows'):
        row = dict(zip(header, line))
        row_dict = {mapped_key: row[col] for mapped_key, col in column_map.items()}

        sample_id = file_sample_id or row_dict.pop(SAMPLE_ID_COL)
        if not (allow_missing_gene or row_dict.get(GENE_ID_COL)):
            missing_required_fields[GENE_ID_COL].add(sample_id)
            continue

        _parse_rna_row(
            sample_id, row_dict, potential_samples, loaded_samples, gene_ids, sample_guid_ids_to_load,
            samples_to_create, unmatched_samples, individual_data_by_id, sample_files, file_dir,
            has_errors=missing_required_fields or (unmatched_samples and not ignore_extra_samples),
        )

    errors, warnings = _process_rna_errors(
        gene_ids, missing_required_fields, unmatched_samples, ignore_extra_samples, loaded_samples,
    )

    if errors:
        raise ErrorsWarningsException(errors)

    if samples_to_create:
        _create_rna_samples(samples_to_create.values(), sample_guid_ids_to_load, user, data_source=data_source, data_type=data_type)

    prev_loaded_individual_ids = _update_existing_sample_models(model_cls, user, data_type, samples_to_create.values(), loaded_samples)

    return warnings, len(loaded_samples) + len(unmatched_samples), sample_guid_ids_to_load, prev_loaded_individual_ids


def _parse_rna_row(sample_id, row_dict, potential_samples, loaded_samples, gene_ids, sample_guid_ids_to_load, samples_to_create,
                   unmatched_samples, individual_data_by_id, sample_files, file_dir, has_errors):

    row_gene_ids = row_dict[GENE_ID_COL].split(';')
    if any(row_gene_ids):
        gene_ids.update(row_gene_ids)

    individual = individual_data_by_id.get(sample_id)
    if not individual:
        unmatched_samples.add(sample_id)
        return

    tissue_type = individual['tissue']
    potential_sample = potential_samples.get((individual['id'], tissue_type))
    if (potential_sample or {}).get('active'):
        loaded_samples.add(potential_sample['guid'])
        return

    if potential_sample:
        sample_guid_ids_to_load[potential_sample['guid']] = sample_id
    elif sample_id not in samples_to_create:
        samples_to_create[sample_id] = {'individual_id': individual['id'], 'tissue_type': tissue_type}

    if has_errors:
        # If there are definite errors, do not process/save data, just continue to check for additional errors
        return

    individual_id = individual['individual_id']
    for gene_id in row_gene_ids:
        row_dict = {**row_dict, GENE_ID_COL: gene_id}
        if individual_id not in sample_files:
            file_name = _get_sample_file_path(file_dir, individual_id)
            sample_files[individual_id] = gzip.open(file_name, 'at')
        sample_files[individual_id].write(f'{json.dumps(row_dict)}\n')


def _get_sample_file_path(file_dir, sample_guid):
    return os.path.join(file_dir, f'{sample_guid}.json.gz')


def _process_rna_errors(gene_ids, missing_required_fields, unmatched_samples, ignore_extra_samples, loaded_samples):
    errors = []
    warnings = []

    matched_gene_ids = set(GeneInfo.objects.filter(gene_id__in=gene_ids).values_list('gene_id', flat=True))
    unknown_gene_ids = gene_ids - matched_gene_ids
    if missing_required_fields:
        errors += [
            f'Samples missing required "{col}": {", ".join(sorted(sample_ids))}'
            for col, sample_ids in missing_required_fields.items()
        ]
    if unknown_gene_ids:
        errors.append(f'Unknown Gene IDs: {", ".join(sorted(unknown_gene_ids))}')

    if unmatched_samples:
        unmatched_sample_ids = ', '.join(sorted(unmatched_samples))
        if ignore_extra_samples:
            warnings.append(f'Skipped loading for the following {len(unmatched_samples)} unmatched samples: {unmatched_sample_ids}')
        else:
            errors.append(f'Unable to find matches for the following samples: {unmatched_sample_ids}')

    if loaded_samples:
        warnings.append(f'Skipped loading for {len(loaded_samples)} samples already loaded from this file')

    return errors, warnings


def _update_existing_sample_models(model_cls, user, data_type, samples_to_create, loaded_samples):
    individual_tissues_to_create = {s['individual_id']: s['tissue_type'] for s in samples_to_create}
    potential_inactivate_samples_by_key = _get_rna_sample_data_by_key(
        individual_id__in=individual_tissues_to_create.keys(), data_type=data_type, is_active=True,
    )
    sample_keys_to_create = set(individual_tissues_to_create.items())
    inactivate_samples = {
        sample['guid']: key[0] for key, sample in potential_inactivate_samples_by_key.items()
        if key in sample_keys_to_create and sample['guid'] not in loaded_samples
    }

    inactivate_sample_guids = RnaSample.bulk_update(
        user, {'is_active': False}, guid__in=inactivate_samples.keys(),
    )

    # Delete old data
    to_delete = model_cls.objects.filter(sample__guid__in=inactivate_sample_guids)
    if to_delete:
        model_cls.bulk_delete(user, to_delete)

    return set(inactivate_samples.values())


def load_rna_seq(request_json, user, **kwargs):
    data_type = request_json['dataType']
    file_path = request_json['file']

    try:
        sample_guids, file_name_prefix, info, warnings = _load_rna_seq(
            data_type, file_path, user, **kwargs,
            tissue=request_json.get('tissue'), ignore_extra_samples=request_json.get('ignoreExtraSamples'),
        )
    except FileNotFoundError:
        return {'error': f'File not found: {file_path}'}, 400
    except ValueError as e:
        return {'error': str(e)}, 400

    return {
        'info': info,
        'warnings': warnings,
        'fileName': file_name_prefix,
        'sampleGuids': sample_guids,
    }, 200


def _load_rna_seq(data_type, file_path, user, sample_metadata_mapping=None, project_guid=None, tissue=None, **kwargs):
    config = RNA_DATA_TYPE_CONFIGS[data_type]
    model_cls = config['model_class']
    data_source = file_path.split('/')[-1].split('_-_')[-1]

    project_guids = [project_guid] if project_guid else {
        metadata['project_guid'] for metadata in sample_metadata_mapping.values()
    }
    projects = Project.objects.filter(guid__in=project_guids)

    individuals = Individual.objects.filter(family__project__in=projects)
    individual_data_by_id = _get_individual_metadata_mapping(sample_metadata_mapping, individuals) if sample_metadata_mapping else {
        i['individual_id']: {**i, 'tissue': tissue} for i in individuals.values('id', 'individual_id')
    }
    potential_samples = _get_rna_sample_data_by_key(
        individual_id__in={i['id'] for i in individual_data_by_id.values()},
        data_type=data_type, data_source=data_source, values={
            'active': F('is_active'),
        },
    )

    sample_files = {}
    file_name_prefix = f'rna_sample_data__{data_type}__{datetime.now().isoformat()}'
    file_dir = get_temp_file_path(file_name_prefix, is_local=True)
    os.mkdir(file_dir)

    warnings, not_loaded_count, sample_guid_ids_to_load, prev_loaded_individual_ids = _load_rna_seq_file(
        file_path, data_source, user, data_type, model_cls, potential_samples, sample_files, file_dir, individual_data_by_id,
        config['columns'], **config['additional_kwargs'], **kwargs)
    message = f'Parsed {len(sample_guid_ids_to_load) + not_loaded_count} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    sample_projects = Project.objects.filter(family__individual__rnasample__guid__in=sample_guid_ids_to_load).values(
        'guid', 'name', new_sample_ids=ArrayAgg(
            'family__individual__individual_id', distinct=True, ordering='family__individual__individual_id',
            filter=~Q(family__individual__id__in=prev_loaded_individual_ids) if prev_loaded_individual_ids else None
        ))
    project_names = ', '.join(sorted([project['name'] for project in sample_projects]))
    project_summary = '' if project_guid else f' in the following {len(sample_projects)} projects: {project_names}'
    message = f'Attempted data loading for {len(sample_guid_ids_to_load)} RNA-seq samples{project_summary}'
    info.append(message)
    logger.info(message, user)

    _notify_rna_loading(model_cls, sample_projects, projects)

    for warning in warnings:
        logger.warning(warning, user)

    for sample_guid, sample_id in sample_guid_ids_to_load.items():
        sample_files[sample_id].close()  # Required to ensure gzipped files are properly terminated
        os.rename(
            _get_sample_file_path(file_dir, sample_id),
            _get_sample_file_path(file_dir, sample_guid),
        )

    if sample_guid_ids_to_load:
        persist_temp_file(file_name_prefix, user)

    return sorted(sample_guid_ids_to_load.keys()), file_name_prefix, info, warnings


def _get_individual_metadata_mapping(sample_metadata_mapping, individuals):
    individuals = individuals.filter(
        individual_id__in=list(sample_metadata_mapping.keys()),
    ).values('id', 'individual_id', 'family__project__guid')
    individual_data_by_id = {}
    for indiv in individuals:
        individual_id = indiv['individual_id']
        sample_metadata = sample_metadata_mapping[individual_id]
        if indiv.pop('family__project__guid') == sample_metadata['project_guid']:
            individual_data = {**indiv, 'tissue': sample_metadata['tissue']}
            individual_data_by_id[individual_id] = individual_data
            # Support when data is provided using either the raw sample ID or the already mapped seqr ID
            if individual_id != sample_metadata['sample_id']:
                individual_data_by_id[sample_metadata['sample_id']] = individual_data
    return individual_data_by_id


def post_process_rna_data(sample_guid, data, get_unique_key=None, format_fields=None):
    mismatches = set()
    invalid_format_fields = defaultdict(set)

    data_by_key = {}
    for row in data:
        is_valid = True
        for key, format_func in (format_fields or {}).items():
            try:
                row[key] = format_func(row[key])
            except Exception:
                is_valid = False
                invalid_format_fields[key].add(row[key])
        if not is_valid:
            continue

        gene_or_unique_id = get_unique_key(row) if get_unique_key else row[GENE_ID_COL]
        existing_data = data_by_key.get(gene_or_unique_id)
        if existing_data and existing_data != row:
            mismatches.add(gene_or_unique_id)
        data_by_key[gene_or_unique_id] = row

    errors = [
        f'Invalid "{col}" values: {", ".join(sorted(values))}' for col, values in invalid_format_fields.items()
    ]
    if mismatches:
        errors.append(f'Error in {sample_guid.split("_", 1)[-1].upper()}: mismatched entries for {", ".join(mismatches)}')

    return data_by_key.values(), '; '.join(errors)


RNA_MODEL_DISPLAY_NAME = {
  RnaSeqOutlier: 'Expression Outlier',
  RnaSeqSpliceOutlier: 'Splice Outlier',
  RnaSeqTpm: 'Expression',
}


def _notify_rna_loading(model_cls, sample_projects, projects):
    projects_by_name = {project.name: project for project in projects}
    data_type = RNA_MODEL_DISPLAY_NAME[model_cls]
    for project_agg in sample_projects:
        new_ids = project_agg["new_sample_ids"]
        project = projects_by_name[project_agg["name"]]
        is_internal = is_internal_anvil_project(project) or not project_has_anvil(project)
        basic_notify_search_data_loaded(project, data_type, 'RNA', new_ids, is_internal=is_internal)


PHENOTYPE_PRIORITIZATION_HEADER = ['tool', 'project', 'sampleId', 'rank', 'geneId', 'diseaseId', 'diseaseName']
PHENOTYPE_PRIORITIZATION_REQUIRED_HEADER = PHENOTYPE_PRIORITIZATION_HEADER + ['scoreName1', 'score1']
MAX_SCORES = 16


def _parse_phenotype_pri_row(row):
    record = {_to_snake_case(key): row.get(key) for key in PHENOTYPE_PRIORITIZATION_HEADER}

    scores = {}
    for i in range(1, MAX_SCORES):
        score_name = row.get(f'scoreName{i}')
        if not score_name:
            break
        # We have both camel case and snake case in the score field names, so convert them to snake case first (those
        # in snake case kept unchanged), then to camel case.
        score = row[f'score{i}']
        if score:
            scores[_to_camel_case(_to_snake_case(score_name))] = float(score)
    record['scores'] = scores

    yield record


def load_phenotype_prioritization_data_file(file_path, user):
    data_by_project_sample_id = defaultdict(lambda: defaultdict(list))
    f = file_iter(file_path, user=user)
    header = _parse_tsv_row(next(f))
    missing_cols = [col for col in PHENOTYPE_PRIORITIZATION_REQUIRED_HEADER if col not in header]
    if missing_cols:
        raise ValueError(f'Invalid file: missing column(s) {", ".join(missing_cols)}')

    tool = None
    for line in tqdm(f, unit=' rows'):
        row = dict(zip(header, _parse_tsv_row(line)))
        for row_dict in _parse_phenotype_pri_row(row):
            sample_id = row_dict.pop('sample_id', None)
            project = row_dict.pop('project', None)
            if not sample_id or not project:
                raise ValueError('Both sample ID and project fields are required.')
            data_by_project_sample_id[project][sample_id].append(row_dict)
            if not tool:
                tool = row_dict['tool']
            elif tool != row_dict['tool']:
                raise ValueError(f'Multiple tools found {tool} and {row_dict["tool"]}. Only one in a file is supported.')

    return tool, data_by_project_sample_id


def convert_django_meta_to_http_headers(request):

    def convert_key(key):
        # converting Django's all-caps keys (eg. 'HTTP_RANGE') to regular HTTP header keys (eg. 'Range')
        return key.replace("HTTP_", "").replace('_', '-').title()

    http_headers = {
        convert_key(key): str(value).lstrip()
        for key, value in request.META.items()
        if key.startswith("HTTP_") or (key in ('CONTENT_LENGTH', 'CONTENT_TYPE') and value)
    }

    return http_headers
