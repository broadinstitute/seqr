from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, F, Q
from django.utils import timezone
from tqdm import tqdm

from seqr.models import Sample, Individual, Family, Project, RnaSample, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier
from seqr.utils.communication_utils import send_project_notification
from seqr.utils.file_utils import file_iter
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.xpos_utils import format_chrom
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.permissions_utils import get_internal_projects
from seqr.views.utils.json_utils import _to_snake_case, _to_camel_case
from reference_data.models import GeneInfo
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

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

    return samples_guids, individual_ids, remaining_sample_keys, loaded_date


def _create_samples(sample_data, user, loaded_date=timezone.now(), **kwargs):
    new_samples = [
        Sample(
            loaded_date=loaded_date,
            **created_sample_data,
            **kwargs,
        ) for created_sample_data in sample_data]
    return Sample.bulk_create(user, new_samples)


def _create_rna_samples(sample_data, sample_guid_keys_to_load, user, **kwargs):
    new_samples = [RnaSample(**sample, **kwargs) for sample in sample_data]
    new_sample_models = RnaSample.bulk_create(user, new_samples)
    new_sample_ids = [s.id for s in new_sample_models]
    sample_key_map = _get_rna_sample_data_by_key(id__in=new_sample_ids)
    sample_guid_keys_to_load.update({s['guid']: sample_key for sample_key, s in sample_key_map.items()})


def _get_rna_sample_data_by_key(values=None, **kwargs):
    key_fields = ['individual__individual_id', 'individual__family__project__name', 'tissue_type']
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
    samples_guids, individual_ids, remaining_sample_keys, loaded_date = _find_or_create_samples(
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
    new_samples = dict(updated_samples.exclude(individual_id__in=previous_loaded_individuals).values_list('id', 'sample_id'))

    return updated_samples, new_samples, inactivated_sample_guids, len(remaining_sample_keys), family_guids_to_update


def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]


PROJECT_COL = 'project'
TISSUE_COL = 'tissue'
SAMPLE_ID_COL = 'sample_id'
SAMPLE_ID_HEADER_COL = 'sampleID'
INDIV_ID_COL = 'individual_id'
GENE_ID_COL = 'gene_id'
GENE_ID_HEADER_COL = 'geneID'
RNA_OUTLIER_COLUMNS = {GENE_ID_COL: GENE_ID_HEADER_COL, 'p_value': 'pValue', 'p_adjust': 'padjust', 'z_score': 'zScore',
                       SAMPLE_ID_COL: SAMPLE_ID_HEADER_COL}

TPM_COL = 'TPM'
TPM_HEADER_COLS = {col.lower(): col for col in [GENE_ID_COL, TPM_COL]}

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

SPLICE_OUTLIER_HEADER_COLS = {col: _to_camel_case(col) for col in SPLICE_OUTLIER_COLS}
SPLICE_OUTLIER_HEADER_COLS.update({
    PROJECT_COL: 'projectName', SAMPLE_ID_COL: SAMPLE_ID_HEADER_COL, GENE_ID_COL: GENE_ID_HEADER_COL,
})

REVERSE_TISSUE_TYPE = dict(RnaSample.TISSUE_TYPE_CHOICES)
TISSUE_TYPE_MAP = {v: k for k, v in REVERSE_TISSUE_TYPE.items()}


def _get_splice_id(row):
    return '-'.join([row[GENE_ID_COL], row[CHROM_COL], str(row[START_COL]), str(row[END_COL]), row[STRAND_COL],
                    row[SPLICE_TYPE_COL]])


RNA_DATA_TYPE_CONFIGS = {
    'outlier': {
        'model_class': RnaSeqOutlier,
        'columns': RNA_OUTLIER_COLUMNS,
        'data_type': RnaSample.DATA_TYPE_EXPRESSION_OUTLIER,
        'additional_kwargs': {},
    },
    'tpm': {
        'model_class': RnaSeqTpm,
        'columns': TPM_HEADER_COLS,
        'data_type': RnaSample.DATA_TYPE_TPM,
        'additional_kwargs': {},
    },
    'splice_outlier': {
        'model_class': RnaSeqSpliceOutlier,
        'columns': SPLICE_OUTLIER_HEADER_COLS,
        'data_type': RnaSample.DATA_TYPE_SPLICE_OUTLIER,
        'additional_kwargs': {
            'allow_missing_gene': True,
        },
        'post_process_kwargs': {
            'get_unique_key': _get_splice_id,
            'format_fields': SPLICE_OUTLIER_FORMATTER,
        },
    },
}


def load_rna_seq(data_type, *args, **kwargs):
    config = RNA_DATA_TYPE_CONFIGS[data_type]
    return _load_rna_seq(config['model_class'], config['data_type'], *args, config['columns'], **config['additional_kwargs'], **kwargs)


def _validate_rna_header(header, column_map):
    required_column_map = {
        column_map.get(col, col): col for col in [SAMPLE_ID_COL, PROJECT_COL, GENE_ID_COL, TISSUE_COL]
    }
    expected_cols = set(column_map.values())
    expected_cols.update(required_column_map.keys())
    missing_cols = expected_cols - set(header)
    if missing_cols:
        raise ValueError(f'Invalid file: missing column(s): {", ".join(sorted(missing_cols))}')
    return required_column_map


def _load_rna_seq_file(
        file_path, data_source, user, data_type, model_cls, potential_samples, save_data, individual_data_by_key,
        column_map, mapping_file=None, allow_missing_gene=False, ignore_extra_samples=False,
):
    sample_id_to_individual_id_mapping = {}
    if mapping_file:
        sample_id_to_individual_id_mapping = load_mapping_file_content(mapping_file)

    f = file_iter(file_path, user=user)
    parsed_f = parse_file(file_path.replace('.gz', ''), f, iter_file=True)
    header = next(parsed_f)
    required_column_map = _validate_rna_header(header, column_map)
    if allow_missing_gene:
        required_column_map = {k: v for k, v in required_column_map.items() if v != GENE_ID_COL}

    loaded_samples = set()
    unmatched_samples = set()
    samples_to_create = {}
    sample_guid_keys_to_load = {}
    missing_required_fields = defaultdict(set)
    gene_ids = set()
    for line in tqdm(parsed_f, unit=' rows'):
        row = dict(zip(header, line))

        row_dict = {mapped_key: row[col] for mapped_key, col in column_map.items()}

        missing_cols = {col_id for col, col_id in required_column_map.items() if not row.get(col)}
        sample_id = row_dict.pop(SAMPLE_ID_COL) if SAMPLE_ID_COL in row_dict else row[SAMPLE_ID_COL]
        if missing_cols:
            for col in missing_cols:
                missing_required_fields[col].add(sample_id)
        if missing_cols:
            continue

        if row.get(INDIV_ID_COL) and sample_id not in sample_id_to_individual_id_mapping:
            sample_id_to_individual_id_mapping[sample_id] = row[INDIV_ID_COL]

        tissue_type = TISSUE_TYPE_MAP[row[TISSUE_COL]]
        project = row_dict.pop(PROJECT_COL, None) or row[PROJECT_COL]
        sample_key = ((sample_id_to_individual_id_mapping or {}).get(sample_id, sample_id), project, tissue_type)

        potential_sample = potential_samples.get(sample_key)
        if (potential_sample or {}).get('active'):
            loaded_samples.add(potential_sample['guid'])
            continue

        row_gene_ids = row_dict[GENE_ID_COL].split(';')
        if any(row_gene_ids):
            gene_ids.update(row_gene_ids)

        if potential_sample:
            sample_guid_keys_to_load[potential_sample['guid']] = sample_key
        else:
            _match_new_sample(
                sample_key, samples_to_create, unmatched_samples, individual_data_by_key,
            )

        if missing_required_fields or (unmatched_samples and not ignore_extra_samples) or (sample_key in unmatched_samples):
            # If there are definite errors, do not process/save data, just continue to check for additional errors
            continue

        for gene_id in row_gene_ids:
            row_dict = {**row_dict, GENE_ID_COL: gene_id}
            save_data(sample_key, row_dict)

    errors, warnings = _process_rna_errors(
        gene_ids, missing_required_fields, unmatched_samples, ignore_extra_samples, loaded_samples,
    )

    if errors:
        raise ErrorsWarningsException(errors)

    if samples_to_create:
        _create_rna_samples(samples_to_create.values(), sample_guid_keys_to_load, user, data_source=data_source, data_type=data_type)

    prev_loaded_individual_ids = _update_existing_sample_models(model_cls, user, data_type, samples_to_create, loaded_samples)

    return warnings, len(loaded_samples) + len(unmatched_samples), sample_guid_keys_to_load, prev_loaded_individual_ids


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
        unmatched_sample_ids = ', '.join(sorted({f'{sample_key[0]} ({sample_key[1]})' for sample_key in unmatched_samples}))
        if ignore_extra_samples:
            warnings.append(f'Skipped loading for the following {len(unmatched_samples)} unmatched samples: {unmatched_sample_ids}')
        else:
            errors.append(f'Unable to find matches for the following samples: {unmatched_sample_ids}')

    if loaded_samples:
        warnings.append(f'Skipped loading for {len(loaded_samples)} samples already loaded from this file')

    return errors, warnings


def _update_existing_sample_models(model_cls, user, data_type, samples_to_create, loaded_samples):
    loaded_individual_ids = [s['individual_id'] for s in samples_to_create.values()]
    potential_inactivate_samples_by_key = _get_rna_sample_data_by_key(
        individual_id__in=loaded_individual_ids, data_type=data_type, is_active=True, values={
            'individual_db_id': F('individual_id'),
        },
    )
    inactivate_samples_by_key = {
        key: sample for key, sample in potential_inactivate_samples_by_key.items()
        if key in samples_to_create and sample['guid'] not in loaded_samples
    }

    inactivate_sample_guids = RnaSample.bulk_update(
        user, {'is_active': False}, guid__in=[s['guid'] for s in inactivate_samples_by_key.values()],
    )

    # Delete old data
    to_delete = model_cls.objects.filter(sample__guid__in=inactivate_sample_guids)
    if to_delete:
        model_cls.bulk_delete(user, to_delete)

    return {s['individual_db_id'] for s in inactivate_samples_by_key.values()}


def _match_new_sample(sample_key, samples_to_create, unmatched_samples, individual_data_by_key):
    if sample_key in samples_to_create or sample_key in unmatched_samples:
        return

    individual_key = sample_key[:2]
    if individual_key in individual_data_by_key:
        samples_to_create[sample_key] = {
            'individual_id': individual_data_by_key[individual_key]['id'],
            'tissue_type': sample_key[2],
        }
    else:
        unmatched_samples.add(sample_key)


def _load_rna_seq(model_cls, data_type, file_path, save_data, *args, user=None, **kwargs):
    projects = get_internal_projects()
    data_source = file_path.split('/')[-1].split('_-_')[-1]

    potential_samples = _get_rna_sample_data_by_key(
        individual__family__project__in=projects, data_type=data_type, data_source=data_source, values={
            'active': F('is_active'),
        },
    )
    individual_data_by_key = _get_individuals_by_key(projects)

    warnings, not_loaded_count, sample_guid_keys_to_load, prev_loaded_individual_ids = _load_rna_seq_file(
        file_path, data_source, user, data_type, model_cls, potential_samples, save_data, individual_data_by_key, *args, **kwargs)
    message = f'Parsed {len(sample_guid_keys_to_load) + not_loaded_count} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    sample_projects = Project.objects.filter(family__individual__rnasample__guid__in=sample_guid_keys_to_load).values(
        'guid', 'name', new_sample_ids=ArrayAgg(
            'family__individual__individual_id', distinct=True, ordering='family__individual__individual_id',
            filter=~Q(family__individual__id__in=prev_loaded_individual_ids) if prev_loaded_individual_ids else None
        ))
    project_names = ', '.join(sorted([project['name'] for project in sample_projects]))
    message = f'Attempted data loading for {len(sample_guid_keys_to_load)} RNA-seq samples in the following {len(sample_projects)} projects: {project_names}'
    info.append(message)
    logger.info(message, user)

    _notify_rna_loading(model_cls, sample_projects, projects)

    for warning in warnings:
        logger.warning(warning, user)

    return sample_guid_keys_to_load, info, warnings


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


def _notify_rna_loading(model_cls, sample_projects, internal_projects):
    projects_by_name = {project.name: project for project in internal_projects}
    data_type = RNA_MODEL_DISPLAY_NAME[model_cls]
    for project_agg in sample_projects:
        new_ids = project_agg["new_sample_ids"]
        send_project_notification(
            project=projects_by_name[project_agg["name"]],
            notification=f'{len(new_ids)} new RNA {data_type} sample(s)',
            subject=f'New RNA {data_type} data available in seqr',
            slack_channel=SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            slack_detail=', '.join(new_ids),
        )


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
