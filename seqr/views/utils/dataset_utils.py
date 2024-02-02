from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, F, Q
from django.utils import timezone
from tqdm import tqdm
import random

from seqr.models import Sample, Individual, Family, Project, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.file_utils import file_iter
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.xpos_utils import format_chrom
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.permissions_utils import get_internal_projects
from seqr.views.utils.json_utils import _to_snake_case, _to_camel_case
from reference_data.models import GeneInfo
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL

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
        tissue_type=None,
        sample_data=None,
):
    sample_params = {'sample_type': sample_type, 'dataset_type': dataset_type, 'tissue_type': tissue_type}
    sample_params.update(sample_data or {})

    samples_by_key = _get_matched_samples_by_key(
        projects, sample_id__in={sample_id for sample_id, _ in sample_project_tuples}, **sample_params,
    )

    existing_samples = {
        key: s for key, s in samples_by_key.items() if key in sample_project_tuples
    }
    remaining_sample_keys = set(sample_project_tuples) - set(existing_samples.keys())

    matched_individual_ids = {sample['individual_id'] for sample in existing_samples.values()}
    loaded_date = timezone.now()
    samples = {**existing_samples}
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
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(
                    len(sample_project_tuples)))
        if raise_unmatched_error_template and remaining_sample_keys:
            raise ValueError(raise_unmatched_error_template.format(
                sample_ids=(', '.join(sorted([sample_id for sample_id, _ in remaining_sample_keys])))))

        # create new Sample records for Individual records that matches
        new_sample_args = {
            sample_key: _get_new_sample_args(sample_key, individual)
            for sample_key, individual in sample_id_to_individual_record.items()
        }
        samples.update(new_sample_args)
        _create_samples(
            new_sample_args.values(),
            user,
            loaded_date=loaded_date,
            **sample_params,
        )
    return samples, remaining_sample_keys, loaded_date


def _create_samples(sample_data, user, loaded_date=timezone.now(), **kwargs):
    new_samples = [
        Sample(
            created_date=timezone.now(),
            loaded_date=loaded_date,
            **created_sample_data,
            **kwargs,
        ) for created_sample_data in sorted(sample_data, key=lambda s: s['guid'])]
    Sample.bulk_create(user, new_samples)


def _get_matched_samples_by_key(projects, key_fields=None, values=None, **sample_params):
    return {
        (s.pop('sample_id'), s.pop('individual__family__project__name'), *[s[field] for field in (key_fields or [])]): s
        for s in Sample.objects.filter(
            individual__family__project__in=projects,
            **sample_params
        ).values('guid', 'individual_id', 'sample_id', 'tissue_type', 'individual__family__project__name', **(values or {}))
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


def _get_new_sample_args(sample_key, individual_data, key_fields=None):
    return {
        'guid': f'S{random.randint(10 ** 9, 10 ** 10)}_{individual_data["individual_id"]}'[:Sample.MAX_GUID_SIZE],  # nosec
        'individual_id': individual_data['id'],
        'sample_id': sample_key[0],
        **{key_field: sample_key[i+2] for i, key_field in enumerate(key_fields or [])}
    }


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
    samples, remaining_sample_keys, loaded_date = _find_or_create_samples(
        sample_project_tuples=sample_project_tuples,
        projects=projects,
        user=user,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_no_match_error=not raise_unmatched_error_template,
        raise_unmatched_error_template=raise_unmatched_error_template,
        sample_type=sample_type,
        dataset_type=dataset_type,
        tissue_type=Sample.NO_TISSUE_TYPE,
        sample_data=sample_data,
    )

    samples_guids = [sample['guid'] for sample in samples.values()]
    individual_ids = {sample['individual_id'] for sample in samples.values()}
    included_families = dict(Family.objects.filter(individual__id__in=individual_ids).values_list('guid', 'analysis_status'))
    _validate_samples_families(samples_guids, included_families.keys(), sample_type, dataset_type, expected_families=expected_families)

    activated_sample_guids, inactivated_sample_guids = _update_variant_samples(
        samples_guids, individual_ids, user, dataset_type, sample_type, sample_data={'loaded_date': loaded_date, **sample_data})
    updated_samples = Sample.objects.filter(guid__in=activated_sample_guids)

    family_guids_to_update = [
        family_guid for family_guid, analysis_status in included_families.items() if analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    return updated_samples, inactivated_sample_guids, len(remaining_sample_keys), family_guids_to_update


def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]


PROJECT_COL = 'project'
TISSUE_COL = 'tissue'
SAMPLE_ID_COL = 'sample_id'
INDIV_ID_COL = 'individual_id'
GENE_ID_COL = 'gene_id'
RNA_OUTLIER_COLUMNS = {GENE_ID_COL: 'geneID', 'p_value': 'pValue', 'p_adjust': 'padjust', 'z_score': 'zScore',
                       SAMPLE_ID_COL: 'sampleID'}

TPM_COL = 'TPM'
TPM_HEADER_COLS = {col.lower(): col for col in [GENE_ID_COL, TPM_COL]}

CHROM_COL = 'chrom'
START_COL = 'start'
END_COL = 'end'
STRAND_COL = 'strand'
READ_COUNT_COL = 'read_count'
SPLICE_TYPE_COL = 'type'
P_VALUE_COL ='p_value'
Z_SCORE_COL = 'z_score'
DELTA_PSI_COL = 'delta_psi'
RARE_DISEASE_SAMPLES_WITH_JUNCTION = 'rare_disease_samples_with_junction'
RARE_DISEASE_SAMPLES_TOTAL = 'rare_disease_samples_total'
SPLICE_OUTLIER_COLS = [
    CHROM_COL, START_COL, END_COL, STRAND_COL, INDIV_ID_COL, SPLICE_TYPE_COL, P_VALUE_COL, Z_SCORE_COL,
    DELTA_PSI_COL, READ_COUNT_COL, GENE_ID_COL, RARE_DISEASE_SAMPLES_WITH_JUNCTION,
    RARE_DISEASE_SAMPLES_TOTAL,
]
SPLICE_OUTLIER_FORMATTER = {
    CHROM_COL: format_chrom,
    START_COL: int,
    END_COL: int,
    READ_COUNT_COL: int,
    RARE_DISEASE_SAMPLES_WITH_JUNCTION: int,
    RARE_DISEASE_SAMPLES_TOTAL: int,
    P_VALUE_COL: float,
    Z_SCORE_COL: float,
    DELTA_PSI_COL: float,
}

SPLICE_OUTLIER_HEADER_COLS = {col: _to_camel_case(col) for col in SPLICE_OUTLIER_COLS}
SPLICE_OUTLIER_HEADER_COLS[SAMPLE_ID_COL] = SPLICE_OUTLIER_HEADER_COLS.pop(INDIV_ID_COL)

REVERSE_TISSUE_TYPE = dict(Sample.TISSUE_TYPE_CHOICES)
TISSUE_TYPE_MAP = {v: k for k, v in REVERSE_TISSUE_TYPE.items() if k != Sample.NO_TISSUE_TYPE}


def load_rna_seq_outlier(*args, **kwargs):
    return _load_rna_seq(RnaSeqOutlier, *args, RNA_OUTLIER_COLUMNS, **kwargs)


def load_rna_seq_tpm(*args, **kwargs):
    return _load_rna_seq(
        RnaSeqTpm, *args, TPM_HEADER_COLS, should_skip=lambda row: row[SAMPLE_ID_COL].startswith('GTEX'), **kwargs,
    )


def _get_splice_id(row):
    return '-'.join([row[GENE_ID_COL], row[CHROM_COL], str(row[START_COL]), str(row[END_COL]), row[STRAND_COL],
                    row[SPLICE_TYPE_COL]])


def load_rna_seq_splice_outlier(*args, **kwargs):
    return _load_rna_seq(
        RnaSeqSpliceOutlier, *args, SPLICE_OUTLIER_HEADER_COLS, format_fields=SPLICE_OUTLIER_FORMATTER,
        get_unique_key=_get_splice_id, allow_missing_gene=True, post_process=_add_splice_rank, **kwargs
    )


def _add_splice_rank(sample_data_rows):
    sorted_data_rows = sorted([data_row for data_row in sample_data_rows.values()], key=lambda d: d[P_VALUE_COL])
    for i, data_row in enumerate(sorted_data_rows):
        data_row['rank'] = i


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


def _parse_rna_row(row, column_map, required_column_map, missing_required_fields, allow_missing_gene, should_skip=None, format_fields=None):
    if not (should_skip and should_skip(row)):
        row_dict = {mapped_key: row[col] for mapped_key, col in column_map.items()}
        for mapped_key, format_func in (format_fields or {}).items():
            row_dict[mapped_key] = format_func(row_dict[mapped_key])

        missing_cols = {col_id for col, col_id in required_column_map.items() if not row.get(col)}
        if allow_missing_gene:
            missing_cols.discard(GENE_ID_COL)
        sample_id = row_dict.pop(SAMPLE_ID_COL) if SAMPLE_ID_COL in row_dict else row[SAMPLE_ID_COL]
        if missing_cols:
            for col in missing_cols:
                missing_required_fields[col].append(sample_id)
        if not missing_cols:
            yield sample_id, row_dict


def _load_rna_seq_file(file_path, user, potential_loaded_samples, potential_samples, individual_data_by_key,
                       update_sample_models, save_data, load_saved_data, column_map, mapping_file=None,
                       get_unique_key=None, allow_missing_gene=False, ignore_extra_samples=False, post_process=None,
                       create_models_before_save=False, **kwargs):

    sample_id_to_individual_id_mapping = {}
    if mapping_file:
        sample_id_to_individual_id_mapping = load_mapping_file_content(mapping_file)

    mismatches = defaultdict(set)
    sample_guids_to_load = set()
    existing_samples_by_guid = {}
    samples_to_create = {}
    created_samples = set()

    def _save_sample_data(sample_guid, sample_data):
        if create_models_before_save:
            update_sample_models(samples_to_create, created_samples, existing_samples_by_guid)
            created_samples.update(samples_to_create.keys())

        prev_data = load_saved_data(sample_guid) or {}
        new_mismatches = {k for k, v in prev_data.items() if k in sample_data and v != sample_data[k]}
        if new_mismatches:
            mismatches[sample_guid].update(new_mismatches)
        sample_data.update(prev_data)

        if post_process:
            post_process(sample_data)

        sample_guids_to_load.add(sample_guid)
        save_data(sample_guid, sample_data)

    samples_by_guid = defaultdict(dict)
    f = file_iter(file_path, user=user)
    parsed_f = parse_file(file_path.replace('.gz', ''), f, iter=True)
    header = next(parsed_f)
    required_column_map = _validate_rna_header(header, column_map)

    loaded_samples = set()
    unmatched_samples = set()
    missing_required_fields = defaultdict(list)
    gene_ids = set()
    current_sample = None
    for line in tqdm(f, unit=' rows'):
        row = dict(zip(header, _parse_tsv_row(line)))
        for sample_id, row_dict in _parse_rna_row(
                row, column_map, required_column_map, missing_required_fields, allow_missing_gene, **kwargs):
            tissue_type = TISSUE_TYPE_MAP[row[TISSUE_COL]]
            project = row[PROJECT_COL]
            sample_key = (sample_id, project, tissue_type)

            if sample_key in potential_loaded_samples:
                loaded_samples.add(sample_key)
                continue

            if row.get(INDIV_ID_COL) and sample_id not in sample_id_to_individual_id_mapping:
                sample_id_to_individual_id_mapping[sample_id] = row[INDIV_ID_COL]

            sample_guid = _get_matched_sample(
                sample_key, potential_samples, unmatched_samples, existing_samples_by_guid, samples_to_create,
                individual_data_by_key, sample_id_to_individual_id_mapping,
            )
            if sample_key in unmatched_samples:
                continue

            gene_id = row_dict[GENE_ID_COL]
            if gene_id:
                gene_ids.add(gene_id)

            if missing_required_fields or (unmatched_samples and not ignore_extra_samples):
                # If there are definite errors, do not process/save data, just continue to check for additional errors
                continue

            if current_sample != sample_guid:
                if len(samples_by_guid[current_sample]) > 5000:
                    _save_sample_data(current_sample, samples_by_guid[current_sample])
                    del samples_by_guid[current_sample]
                current_sample = sample_guid

            if get_unique_key:
                gene_or_unique_id = get_unique_key(row_dict)
            else:
                gene_or_unique_id = gene_id
            existing_data = samples_by_guid[sample_guid].get(gene_or_unique_id)
            if existing_data and existing_data != row_dict:
                mismatches[sample_guid].add(gene_or_unique_id)

            samples_by_guid[sample_guid][gene_or_unique_id] = row_dict

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
        unmatched_sample_ids = ', '.join(sorted([sample_key[0] for sample_key in unmatched_samples]))
        if ignore_extra_samples:
            warnings.append(f'Skipped loading for the following {len(unmatched_samples)} unmatched samples: {unmatched_sample_ids}')
        else:
            errors.append(f'Unable to find matches for the following samples: {unmatched_sample_ids}')

    if not errors:
        for sample_guid, sample_data in samples_by_guid.items():
            if sample_data:
                _save_sample_data(sample_guid, sample_data)

    if mismatches:
        errors = [
            f'Error in {sample_guid.split("_", 1)[-1].upper()}: mismatched entries for {", ".join(mismatch_ids)}'
            for sample_guid, mismatch_ids in mismatches.items()
        ] + errors

    if errors:
        raise ErrorsWarningsException(errors)

    if loaded_samples:
        warnings.append(f'Skipped loading for {len(loaded_samples)} samples already loaded from this file')

    if not create_models_before_save:
        update_sample_models(samples_to_create, created_samples, existing_samples_by_guid)

    return warnings, sample_guids_to_load, len(loaded_samples) + len(unmatched_samples)


def _get_matched_sample(sample_key, potential_samples, unmatched_samples, existing_samples_by_guid, samples_to_create,
                        individual_data_by_key, sample_id_to_individual_id_mapping):
    if sample_key in potential_samples:
        sample = potential_samples[sample_key]
        sample_guid = sample['guid']
        existing_samples_by_guid[sample_guid] = sample
        return sample_guid

    if sample_key not in samples_to_create and sample_key not in unmatched_samples:
        individual_key = _get_individual_key(sample_key, sample_id_to_individual_id_mapping)
        if individual_key in individual_data_by_key:
            samples_to_create[sample_key] = _get_new_sample_args(
                sample_key, individual_data_by_key[individual_key], key_fields=['tissue_type'],
            )
        else:
            unmatched_samples.add(sample_key)

    return samples_to_create.get(sample_key, {}).get('guid')


def _load_rna_seq(model_cls, file_path, *args, user=None, **kwargs):
    projects = get_internal_projects()
    data_source = file_path.split('/')[-1].split('_-_')[-1]

    potential_samples = _get_matched_samples_by_key(
        projects, sample_type=Sample.SAMPLE_TYPE_RNA, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        key_fields=['tissue_type'], values={
            'dataSource': F('data_source'),
            'model_count': Count(model_cls.__name__.lower()),
            'active': F('is_active'),
        },
    )
    potential_loaded_samples = {key for key, s in potential_samples.items() if s['dataSource'] == data_source and s['active']}
    individual_id_by_key = _get_individuals_by_key(projects)
    prev_loaded_individual_ids = set()

    def update_sample_models(possible_samples_to_create, created_samples, existing_samples_by_guid):
        samples_to_create = [s for key, s in possible_samples_to_create.items() if key not in created_samples]
        if samples_to_create:
            _create_samples(
                samples_to_create,
                user=user,
                data_source=data_source,
                sample_type=Sample.SAMPLE_TYPE_RNA,
                dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            )

        # Delete old data
        to_delete_sample_individuals = {
            guid: s['individual_id'] for guid, s in existing_samples_by_guid.items()
            if s['model_count'] > 0 and s['dataSource'] != data_source
        }
        prev_loaded_individual_ids.update(to_delete_sample_individuals.values())
        to_delete = model_cls.objects.filter(sample__guid__in=to_delete_sample_individuals.keys())
        if to_delete:
            model_cls.bulk_delete(user, to_delete)

        Sample.bulk_update(user, {'data_source': data_source}, guid__in=existing_samples_by_guid)

    warnings, sample_guids_to_load, not_loaded_count = _load_rna_seq_file(
        file_path, user, potential_loaded_samples, potential_samples, individual_id_by_key, update_sample_models,
        *args, **kwargs)
    message = f'Parsed {len(sample_guids_to_load) + not_loaded_count} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    sample_projects = Project.objects.filter(family__individual__sample__guid__in=sample_guids_to_load).values(
        'guid', 'name', new_sample_ids=ArrayAgg(
            'family__individual__sample__sample_id', distinct=True, ordering='family__individual__sample__sample_id',
            filter=~Q(family__individual__id__in=prev_loaded_individual_ids) if prev_loaded_individual_ids else None
        ))
    project_names = ', '.join(sorted([project['name'] for project in sample_projects]))
    message = f'Attempted data loading for {len(sample_guids_to_load)} RNA-seq samples in the following {len(sample_projects)} projects: {project_names}'
    info.append(message)
    logger.info(message, user)

    _notify_rna_loading(model_cls, sample_projects)

    for warning in warnings:
        logger.warning(warning, user)

    return sample_guids_to_load, info, warnings


RNA_MODEL_DISPLAY_NAME = {
  RnaSeqOutlier: 'Expression Outlier',
  RnaSeqSpliceOutlier: 'Splice Outlier',
  RnaSeqTpm: 'Expression',
}

def _notify_rna_loading(model_cls, sample_projects):
    data_type = RNA_MODEL_DISPLAY_NAME[model_cls]
    for project_agg in sample_projects:
        new_ids = project_agg["new_sample_ids"]
        project_link = f'<{BASE_URL}project/{project_agg["guid"]}/project_page|{project_agg["name"]}>'
        safe_post_to_slack(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            f'{len(new_ids)} new RNA {data_type} samples are loaded in {project_link}\n```{", ".join(new_ids)}```'
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
