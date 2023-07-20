from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import prefetch_related_objects, Q
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


def _get_individual_sample_lookup(individuals):
    return {i.individual_id: i for i in individuals}


def _get_mapped_individual_lookup_key(sample_id_to_individual_id_mapping):
    sample_id_to_individual_id_mapping = sample_id_to_individual_id_mapping or {}

    def _get_mapped_id(sample_id):
        return sample_id_to_individual_id_mapping.get(sample_id, sample_id)
    return _get_mapped_id


def _find_or_create_missing_sample_records(
        samples,
        projects,
        user,
        sample_count,
        get_individual_sample_key,
        remaining_sample_keys,
        raise_no_match_error=False,
        get_unmatched_error=None,
        create_active=False,
        get_individual_sample_lookup=_get_individual_sample_lookup,
        sample_id_to_tissue_type=None,
        **kwargs
):
    samples = list(samples)
    matched_individual_ids = {sample.individual_id for sample in samples}
    if len(remaining_sample_keys) > 0:
        remaining_individuals_dict = get_individual_sample_lookup(
            Individual.objects.filter(family__project__in=projects).exclude(id__in=matched_individual_ids)
        )

        # find Individual records with exactly-matching individual_ids
        sample_id_to_individual_record = {}
        for sample_key in remaining_sample_keys:
            individual_key = get_individual_sample_key(sample_key)
            if individual_key not in remaining_individuals_dict:
                continue
            sample_id_to_individual_record[sample_key] = remaining_individuals_dict[individual_key]
            del remaining_individuals_dict[individual_key]

        logger.debug(str(len(sample_id_to_individual_record)) + " matched individual ids", user)

        remaining_sample_keys -= set(sample_id_to_individual_record.keys())
        if raise_no_match_error and len(remaining_sample_keys) == sample_count:
            raise ValueError(
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(sample_count))
        if get_unmatched_error and remaining_sample_keys:
            raise ValueError(get_unmatched_error(remaining_sample_keys))

        # create new Sample records for Individual records that matches
        new_samples = [
            Sample(
                guid='S{}_{}'.format(random.randint(10**9, 10**10), individual.individual_id)[:Sample.MAX_GUID_SIZE], # nosec
                sample_id=sample_key[0] if isinstance(sample_key, tuple) else sample_key,
                individual=individual,
                created_date=timezone.now(),
                is_active=create_active,
                tissue_type=sample_id_to_tissue_type.get(sample_key) if sample_id_to_tissue_type else None,
                **kwargs
            ) for sample_key, individual in sample_id_to_individual_record.items()]
        samples += list(Sample.bulk_create(user, new_samples))

    return samples, matched_individual_ids, remaining_sample_keys


def _validate_samples_families(samples, included_families, sample_type, dataset_type, expected_families=None):
    missing_individuals = Individual.objects.filter(
        family__in=included_families,
        sample__is_active=True,
        sample__dataset_type=dataset_type,
        sample__sample_type=sample_type,
    ).exclude(sample__in=samples).select_related('family')
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
        missing_families = expected_families - included_families
        if missing_families:
            raise ValueError(
                'The following families have saved variants but are missing from the callset: {}.'.format(
                    ', '.join([f.family_id for f in missing_families])
                ))


def _update_variant_samples(samples, user, dataset_type, sample_type, sample_data):
    updated_samples = [sample.id for sample in samples]

    activated_sample_guids = Sample.bulk_update(user, {
        'is_active': True,
        **sample_data,
    }, id__in=updated_samples, is_active=False)

    inactivate_samples = Sample.objects.filter(
        individual_id__in={sample.individual_id for sample in samples},
        is_active=True,
        dataset_type=dataset_type,
        sample_type=sample_type,
    ).exclude(id__in=updated_samples)

    inactivate_sample_guids = Sample.bulk_update(user, {'is_active': False}, queryset=inactivate_samples)

    return activated_sample_guids, inactivate_sample_guids


def match_and_update_search_samples(
        project, user, sample_ids, sample_type, dataset_type, sample_data,
        sample_id_to_individual_id_mapping, raise_unmatched_error_template, expected_families=None,
):
    def _get_unmatched_error(remaining_sample_ids):
        return raise_unmatched_error_template.format(sample_ids=(', '.join(sorted(remaining_sample_ids))))

    samples = Sample.objects.select_related('individual').filter(
        individual__family__project=project,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids,
        **sample_data,
    )
    loaded_date = timezone.now()
    samples, matched_individual_ids, _ = _find_or_create_missing_sample_records(
        samples=samples,
        projects=[project],
        user=user,
        sample_count=len(sample_ids),
        get_individual_sample_key=_get_mapped_individual_lookup_key(sample_id_to_individual_id_mapping),
        remaining_sample_keys=set(sample_ids) - {sample.sample_id for sample in samples},
        raise_no_match_error=not raise_unmatched_error_template,
        get_unmatched_error=_get_unmatched_error if raise_unmatched_error_template else None,
        sample_type=sample_type,
        dataset_type=dataset_type,
        loaded_date=loaded_date,
        **sample_data,
    )

    prefetch_related_objects(samples, 'individual__family')
    included_families = {sample.individual.family for sample in samples}
    _validate_samples_families(samples, included_families, sample_type, dataset_type, expected_families=expected_families)

    activated_sample_guids, inactivated_sample_guids = _update_variant_samples(
        samples, user, dataset_type, sample_type, sample_data={'loaded_date': loaded_date, **sample_data})

    family_guids_to_update = [
        family.guid for family in included_families if family.analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    sample_ids = [s.id for s in samples]
    return sample_ids, matched_individual_ids, activated_sample_guids, inactivated_sample_guids, family_guids_to_update


def _match_and_update_rna_samples(
    projects, user, sample_project_tuples, data_source, sample_id_to_individual_id_mapping, raise_unmatched_error_template,
    sample_id_to_tissue_type,
):
    def _get_unmatched_error(sample_keys):
        return raise_unmatched_error_template.format(sample_ids=(', '.join(sorted([sample_id for sample_id, _ in sample_keys]))))

    query = Q(
        individual__family__project__in=projects,
        sample_type=Sample.SAMPLE_TYPE_RNA,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_id__in={sample_id for sample_id, _ in sample_project_tuples},
    )
    tissues = set(sample_id_to_tissue_type.values())
    query &= Q(tissue_type__isnull=True) if tissues == {None} else Q(tissue_type__in=tissues)
    samples = Sample.objects.select_related('individual__family__project').filter(query)

    existing_samples = [s for s in samples if (s.sample_id, s.individual.family.project.name) in sample_project_tuples
                        and sample_id_to_tissue_type[(s.sample_id, s.individual.family.project.name)] == s.tissue_type]

    samples, _, remaining_sample_keys = _find_or_create_missing_sample_records(
        samples=existing_samples,
        projects=projects,
        user=user,
        sample_count=len(sample_project_tuples),
        get_individual_sample_key=lambda key: (sample_id_to_individual_id_mapping.get(key[0], key[0]), key[1]),
        remaining_sample_keys=set(sample_project_tuples) -
                              {(s.sample_id, s.individual.family.project.name) for s in existing_samples},
        raise_no_match_error=False,
        get_unmatched_error=_get_unmatched_error if raise_unmatched_error_template else None,
        create_active=True,
        get_individual_sample_lookup=lambda inds: {(i.individual_id, i.family.project.name):
                                                       i for i in inds.select_related('family__project')},
        sample_id_to_tissue_type=sample_id_to_tissue_type,
        data_source=data_source,
        sample_type=Sample.SAMPLE_TYPE_RNA,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        loaded_date=timezone.now(),
    )

    return existing_samples, samples, {sample_id for sample_id, _ in remaining_sample_keys}

def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]

PROJECT_COL = 'project'
RNA_OUTLIER_COLUMNS = {'geneID': 'gene_id', 'pValue': 'p_value', 'padjust': 'p_adjust', 'zScore': 'z_score',
                       PROJECT_COL: PROJECT_COL}

SAMPLE_ID_COL = 'sample_id'
GENE_ID_COL = 'gene_id'
TPM_COL = 'TPM'
TISSUE_COL = 'tissue'
INDIV_ID_COL = 'individual_id'
TPM_HEADER_COLS = [SAMPLE_ID_COL, PROJECT_COL, GENE_ID_COL, TISSUE_COL, TPM_COL]

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
    DELTA_PSI_COL, READ_COUNT_COL, GENE_ID_COL, TISSUE_COL, RARE_DISEASE_SAMPLES_WITH_JUNCTION,
    RARE_DISEASE_SAMPLES_TOTAL, PROJECT_COL
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

TISSUE_TYPE_MAP = {
    'whole_blood': 'WB',
    'fibroblasts': 'F',
    'muscle': 'M',
    'lymphocytes': 'L',
}

REVERSE_TISSUE_TYPE = {v: k for k, v in TISSUE_TYPE_MAP.items()}


def _parse_outlier_row(row):
    yield row['sampleID'], {mapped_key: row[key] for key, mapped_key in RNA_OUTLIER_COLUMNS.items()}


def _parse_splice_outlier_row(row):
    parsed = {
        key: SPLICE_OUTLIER_FORMATTER[key](row[col]) if SPLICE_OUTLIER_FORMATTER.get(key) else row[col]
        for key, col in SPLICE_OUTLIER_HEADER_COLS.items()
    }
    yield parsed[INDIV_ID_COL], parsed

def _parse_tpm_row(row):
    sample_id = row[SAMPLE_ID_COL]
    if not sample_id.startswith('GTEX'):
        tissue = row[TISSUE_COL]
        if not tissue:
            raise ValueError(f'Sample {sample_id} has no tissue type')

        parsed = {GENE_ID_COL: row[GENE_ID_COL], 'tpm': row[TPM_COL], PROJECT_COL: row[PROJECT_COL], TISSUE_COL: tissue}
        if INDIV_ID_COL in row:
            parsed[INDIV_ID_COL] = row[INDIV_ID_COL]

        yield sample_id, parsed

def load_rna_seq_outlier(file_path, user=None, mapping_file=None, ignore_extra_samples=False):
    expected_columns = ['sampleID'] + list(RNA_OUTLIER_COLUMNS.keys())
    return _load_rna_seq(
        RnaSeqOutlier, file_path, user, mapping_file, ignore_extra_samples, _parse_outlier_row, expected_columns,
    )

def load_rna_seq_tpm(file_path, user=None, mapping_file=None, ignore_extra_samples=False):
    return _load_rna_seq(
        RnaSeqTpm, file_path, user, mapping_file, ignore_extra_samples, _parse_tpm_row, TPM_HEADER_COLS,
   )


def _get_splice_id(row):
    return '-'.join([row[GENE_ID_COL], row[CHROM_COL], str(row[START_COL]), str(row[END_COL]), row[STRAND_COL],
                    row[SPLICE_TYPE_COL]])


def load_rna_seq_splice_outlier(file_path, user=None, mapping_file=None, ignore_extra_samples=False):
    samples_to_load, info, warnings = _load_rna_seq(
        RnaSeqSpliceOutlier, file_path, user, mapping_file, ignore_extra_samples, _parse_splice_outlier_row,
        SPLICE_OUTLIER_HEADER_COLS.values(), get_unique_key=_get_splice_id
    )

    for sample_data_rows in samples_to_load.values():
        sorted_data_rows = sorted([data_row for data_row in sample_data_rows.values()], key=lambda d: d[P_VALUE_COL])
        for i, data_row in enumerate(sorted_data_rows):
            data_row['rank'] = i

    return samples_to_load, info, warnings


def _load_rna_seq_file(file_path, user, mapping_file, parse_row, expected_columns, get_unique_key):

    sample_id_to_individual_id_mapping = {}
    if mapping_file:
        sample_id_to_individual_id_mapping = load_mapping_file_content(mapping_file)

    samples_by_id = defaultdict(dict)
    f = file_iter(file_path, user=user)
    header = _parse_tsv_row(next(f))
    missing_cols = set(expected_columns) - set(header)
    if missing_cols:
        raise ValueError(f'Invalid file: missing column(s): {", ".join(sorted(missing_cols))}')

    sample_id_to_tissue_type = {}
    samples_with_conflict_tissues = defaultdict(set)
    errors = []
    gene_ids = set()
    for line in tqdm(f, unit=' rows'):
        row = dict(zip(header, _parse_tsv_row(line)))
        for sample_id, row_dict in parse_row(row):
            tissue_type = TISSUE_TYPE_MAP.get(row_dict.pop(TISSUE_COL, None))
            project = row_dict.pop(PROJECT_COL)
            indiv_id = row_dict.pop(INDIV_ID_COL, None)
            if (sample_id, project) in sample_id_to_tissue_type:
                prev_tissue_type = sample_id_to_tissue_type[(sample_id, project)]
                if tissue_type != prev_tissue_type:
                    samples_with_conflict_tissues[(sample_id, project)].update({prev_tissue_type, tissue_type})
                    continue

            sample_id_to_tissue_type[(sample_id, project)] = tissue_type

            gene_ids.add(row_dict[GENE_ID_COL])

            if get_unique_key:
                gene_or_unique_id = get_unique_key(row_dict)
            else:
                gene_or_unique_id = row_dict[GENE_ID_COL]
            existing_data = samples_by_id[(sample_id, project)].get(gene_or_unique_id)
            if existing_data and existing_data != row_dict:
                errors.append(f'Error in {sample_id} data for {gene_or_unique_id}: mismatched entries '
                              f'{existing_data} and {row_dict}')

            if indiv_id and sample_id not in sample_id_to_individual_id_mapping:
                sample_id_to_individual_id_mapping[sample_id] = indiv_id

            samples_by_id[(sample_id, project)][gene_or_unique_id] = row_dict

    matched_gene_ids = set(GeneInfo.objects.filter(gene_id__in=gene_ids).values_list('gene_id', flat=True))
    unknown_gene_ids = gene_ids - matched_gene_ids
    if unknown_gene_ids:
        errors.append(f'Unknown Gene IDs: {", ".join(sorted(unknown_gene_ids))}')

    if errors:
        raise ErrorsWarningsException(errors)

    tissue_conflict_messages = []
    for (sample_id, project), tissue_types in samples_with_conflict_tissues.items():
        sample_id_to_tissue_type.pop((sample_id, project))
        samples_by_id.pop((sample_id, project))
        tissue_conflict_messages.append(
            f'{sample_id} ({", ".join(sorted([REVERSE_TISSUE_TYPE[tissue_type] for tissue_type in tissue_types]))})')
    warnings = [f'Skipped data loading for the following {len(samples_with_conflict_tissues)} sample(s) due to mismatched'
                f' tissue type: {", ".join(tissue_conflict_messages)}'] if samples_with_conflict_tissues else []

    return warnings, samples_by_id, sample_id_to_individual_id_mapping, sample_id_to_tissue_type


def _load_rna_seq(model_cls, file_path, user, mapping_file, ignore_extra_samples, parse_row, expected_columns,
                      get_unique_key=None):
    warnings, samples_by_id, sample_id_to_individual_id_mapping, sample_id_to_tissue_type = _load_rna_seq_file(
        file_path, user, mapping_file, parse_row, expected_columns, get_unique_key)
    message = f'Parsed {len(samples_by_id)} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    data_source = file_path.split('/')[-1].split('_-_')[-1]
    existing_samples, samples, remaining_sample_ids = _match_and_update_rna_samples(
        projects=get_internal_projects(),
        user=user,
        sample_project_tuples=samples_by_id.keys(),
        data_source=data_source,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_unmatched_error_template=None if ignore_extra_samples else 'Unable to find matches for the following samples: {sample_ids}',
        sample_id_to_tissue_type=sample_id_to_tissue_type,
    )

    # Delete old data
    to_delete = model_cls.objects.filter(sample__in=samples).exclude(sample__data_source=data_source)
    prev_loaded_individual_ids = set(to_delete.values_list('sample__individual_id', flat=True))
    if to_delete:
        model_cls.bulk_delete(user, to_delete)

    Sample.bulk_update(user, {'data_source': data_source}, id__in={s.id for s in existing_samples})

    loaded_sample_ids = set(model_cls.objects.filter(sample__in=samples).values_list('sample_id', flat=True).distinct())
    prefetch_related_objects(samples, 'individual__family__project')  # newly created samples need prefetching
    samples_to_load = {
        sample: samples_by_id[(sample.sample_id, sample.individual.family.project.name)] for sample in samples\
        if sample.id not in loaded_sample_ids
    }

    sample_projects = Project.objects.filter(family__individual__sample__in=samples_to_load.keys()).values(
        'guid', 'name', new_sample_ids=ArrayAgg(
            'family__individual__sample__sample_id', distinct=True, ordering='family__individual__sample__sample_id',
            filter=~Q(family__individual__id__in=prev_loaded_individual_ids) if prev_loaded_individual_ids else None
        ))
    project_names = ', '.join(sorted([project['name'] for project in sample_projects]))
    message = f'Attempted data loading for {len(samples_to_load)} RNA-seq samples in the following {len(sample_projects)} projects: {project_names}'
    info.append(message)
    logger.info(message, user)

    _notify_rna_loading(model_cls, sample_projects)

    if remaining_sample_ids:
        skipped_samples = ', '.join(sorted(remaining_sample_ids))
        message = f'Skipped loading for the following {len(remaining_sample_ids)} unmatched samples: {skipped_samples}'
        warnings.append(message)
    if loaded_sample_ids:
        message = f'Skipped loading for {len(loaded_sample_ids)} samples already loaded from this file'
        warnings.append(message)

    for warning in warnings:
        logger.warning(warning, user)

    return samples_to_load, info, warnings


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
