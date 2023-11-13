from collections import defaultdict
from copy import deepcopy

from datetime import datetime
from dateutil import relativedelta as rdelta
from django.db.models import Prefetch, Count, Q, F
from django.utils import timezone
import json
import re
import requests

from seqr.utils.file_utils import is_google_bucket_file_path, does_file_exist
from seqr.utils.gene_utils import get_genes
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.xpos_utils import get_chrom_pos

from seqr.views.utils.airtable_utils import get_airtable_samples
from seqr.views.utils.anvil_metadata_utils import parse_anvil_metadata, HISPANIC, MIDDLE_EASTERN, OTHER_POPULATION, \
    ANCESTRY_MAP, ANCESTRY_DETAIL_MAP, SHARED_DISCOVERY_TABLE_VARIANT_COLUMNS, FAMILY_ROW_TYPE, SUBJECT_ROW_TYPE, \
    SAMPLE_ROW_TYPE, DISCOVERY_ROW_TYPE
from seqr.views.utils.export_utils import export_multiple_files, write_multiple_files_to_gs
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import analyst_required, get_project_and_check_permissions, \
    check_project_permissions, get_project_guids_user_can_view, get_internal_projects
from seqr.views.utils.terra_api_utils import anvil_enabled
from seqr.views.utils.variant_utils import get_variant_main_transcript, get_saved_discovery_variants_by_family, \
    get_variant_inheritance_models, get_sv_name, get_discovery_phenotype_class

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant, Individual, FamilyNote
from reference_data.models import Omim, HumanPhenotypeOntology, GENOME_VERSION_LOOKUP
from settings import GREGOR_DATA_MODEL_URL


logger = SeqrLogger(__name__)

MONDO_BASE_URL = 'https://monarchinitiative.org/v3/api/entity'


@analyst_required
def seqr_stats(request):
    non_demo_projects = Project.objects.filter(is_demo=False)

    project_models = {
        'demo': Project.objects.filter(is_demo=True),
    }
    if anvil_enabled():
        is_anvil_q = Q(workspace_namespace='') | Q(workspace_namespace__isnull=True)
        anvil_projects = non_demo_projects.exclude(is_anvil_q)
        internal_ids = get_internal_projects().values_list('id', flat=True)
        project_models.update({
            'internal': anvil_projects.filter(id__in=internal_ids),
            'external': anvil_projects.exclude(id__in=internal_ids),
            'no_anvil': non_demo_projects.filter(is_anvil_q),
        })
    else:
        project_models.update({
            'non_demo': non_demo_projects,
        })

    grouped_sample_counts = defaultdict(dict)
    for project_key, projects in project_models.items():
        samples_counts = _get_sample_counts(Sample.objects.filter(individual__family__project__in=projects))
        for k, v in samples_counts.items():
            grouped_sample_counts[k][project_key] = v

    return create_json_response({
        'projectsCount': {k: projects.count() for k, projects in project_models.items()},
        'familiesCount': {
            k: Family.objects.filter(project__in=projects).count() for k, projects in project_models.items()
        },
        'individualsCount': {
            k: Individual.objects.filter(family__project__in=projects).count() for k, projects in project_models.items()
        },
        'sampleCountsByType': grouped_sample_counts,
    })


def _get_sample_counts(sample_q):
    samples_agg = sample_q.filter(is_active=True).values('sample_type', 'dataset_type').annotate(count=Count('*'))
    return {
        f'{sample_agg["sample_type"]}__{sample_agg["dataset_type"]}': sample_agg['count'] for sample_agg in samples_agg
    }


# AnVIL metadata

SUBJECT_TABLE_COLUMNS = [
    'entity:subject_id', 'subject_id', 'prior_testing', 'project_id', 'pmid_id', 'dbgap_study_id',
    'dbgap_subject_id', 'multiple_datasets', 'family_id', 'paternal_id', 'maternal_id', 'twin_id',
    'proband_relationship', 'sex', 'ancestry', 'ancestry_detail', 'age_at_last_observation', 'phenotype_group',
    'disease_id', 'disease_description', 'affected_status', 'congenital_status', 'age_of_onset', 'hpo_present',
    'hpo_absent', 'phenotype_description', 'solve_state',
]
SAMPLE_TABLE_COLUMNS = [
    'entity:sample_id', 'subject_id', 'sample_id', 'dbgap_sample_id', 'sequencing_center', 'sample_source',
    'tissue_affected_status',
]
FAMILY_TABLE_COLUMNS = [
    'entity:family_id', 'family_id', 'consanguinity', 'consanguinity_detail', 'pedigree_image', 'pedigree_detail',
    'family_history', 'family_onset',
]
DISCOVERY_TABLE_CORE_COLUMNS = ['subject_id', 'sample_id']
DISCOVERY_TABLE_VARIANT_COLUMNS = list(SHARED_DISCOVERY_TABLE_VARIANT_COLUMNS)
DISCOVERY_TABLE_VARIANT_COLUMNS.insert(4, 'variant_genome_build')
DISCOVERY_TABLE_VARIANT_COLUMNS.insert(14, 'significance')

GENOME_BUILD_MAP = {
    '37': 'GRCh37',
    '38': 'GRCh38.p12',
}


@analyst_required
def anvil_export(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    parsed_rows = defaultdict(list)

    def _add_row(row, family_id, row_type):
        if row_type == DISCOVERY_ROW_TYPE:
            parsed_rows[row_type] += [{
                'entity:discovery_id': f'{discovery_row["Chrom"]}_{discovery_row["Pos"]}_{discovery_row["subject_id"]}',
                **discovery_row,
            } for discovery_row in row]
        else:
            id_field = f'{row_type}_id'
            entity_id_field = f'entity:{id_field}'
            if id_field in row and entity_id_field not in row:
                row[entity_id_field] = row[id_field]
            parsed_rows[row_type].append(row)

    parse_anvil_metadata(
        [project], request.GET.get('loadedBefore'), request.user, _add_row,
        get_additional_variant_fields=lambda variant, genome_version: {
            'variant_genome_build': GENOME_BUILD_MAP.get(variant.get('genomeVersion') or genome_version) or '',
        },
        get_additional_sample_fields=lambda sample, *args: {
            'entity:sample_id': sample.individual.individual_id,
            'sequencing_center': 'Broad',
        },
    )

    return export_multiple_files([
        ['{}_PI_Subject'.format(project.name), SUBJECT_TABLE_COLUMNS, parsed_rows[SUBJECT_ROW_TYPE]],
        ['{}_PI_Sample'.format(project.name), SAMPLE_TABLE_COLUMNS, parsed_rows[SAMPLE_ROW_TYPE]],
        ['{}_PI_Family'.format(project.name), FAMILY_TABLE_COLUMNS, parsed_rows[FAMILY_ROW_TYPE]],
        ['{}_PI_Discovery'.format(project.name), ['entity:discovery_id'] + DISCOVERY_TABLE_CORE_COLUMNS + DISCOVERY_TABLE_VARIANT_COLUMNS, parsed_rows[DISCOVERY_ROW_TYPE]],
    ], '{}_AnVIL_Metadata'.format(project.name), add_header_prefix=True, file_format='tsv', blank_value='-')


# GREGoR metadata

GREGOR_DATA_TYPES = ['wgs', 'wes', 'rna']
SMID_FIELD = 'SMID'
PARTICIPANT_ID_FIELD = 'CollaboratorParticipantID'
COLLABORATOR_SAMPLE_ID_FIELD = 'CollaboratorSampleID'
PARTICIPANT_TABLE_COLUMNS = {
    'participant_id', 'internal_project_id', 'gregor_center', 'consent_code', 'recontactable', 'prior_testing',
    'pmid_id', 'family_id', 'paternal_id', 'maternal_id', 'proband_relationship',
    'sex', 'reported_race', 'reported_ethnicity', 'ancestry_detail', 'solve_status', 'missing_variant_case',
    'age_at_last_observation', 'affected_status', 'phenotype_description', 'age_at_enrollment',
}
GREGOR_FAMILY_TABLE_COLUMNS = {'family_id', 'consanguinity'}
PHENOTYPE_TABLE_COLUMNS = {
    'phenotype_id', 'participant_id', 'term_id', 'presence', 'ontology', 'additional_details', 'onset_age_range',
    'additional_modifiers',
}
ANALYTE_TABLE_COLUMNS = {
    'analyte_id', 'participant_id', 'analyte_type', 'primary_biosample', 'tissue_affected_status',
}
EXPERIMENT_TABLE_AIRTABLE_FIELDS = [
    'seq_library_prep_kit_method', 'read_length', 'experiment_type', 'targeted_regions_method',
    'targeted_region_bed_file', 'date_data_generation', 'target_insert_size', 'sequencing_platform',
]
EXPERIMENT_COLUMNS = {'analyte_id', 'experiment_sample_id'}
EXPERIMENT_TABLE_COLUMNS = {'experiment_dna_short_read_id'}
EXPERIMENT_TABLE_COLUMNS.update(EXPERIMENT_COLUMNS)
EXPERIMENT_TABLE_COLUMNS.update(EXPERIMENT_TABLE_AIRTABLE_FIELDS)
EXPERIMENT_RNA_TABLE_AIRTABLE_FIELDS = [
    'library_prep_type', 'single_or_paired_ends', 'within_site_batch_name', 'RIN', 'estimated_library_size',
    'total_reads', 'percent_rRNA', 'percent_mRNA', '5prime3prime_bias',
]
EXPERIMENT_RNA_TABLE_COLUMNS = {'experiment_rna_short_read_id'}
EXPERIMENT_RNA_TABLE_COLUMNS.update(EXPERIMENT_COLUMNS)
EXPERIMENT_RNA_TABLE_COLUMNS.update(EXPERIMENT_RNA_TABLE_AIRTABLE_FIELDS)
EXPERIMENT_RNA_TABLE_COLUMNS.update([c for c in EXPERIMENT_TABLE_AIRTABLE_FIELDS if not c.startswith('target')])
EXPERIMENT_LOOKUP_TABLE_COLUMNS = {'experiment_id', 'table_name', 'id_in_table', 'participant_id'}
READ_TABLE_AIRTABLE_FIELDS = [
    'aligned_dna_short_read_file', 'aligned_dna_short_read_index_file', 'md5sum', 'reference_assembly',
    'mean_coverage', 'alignment_software', 'analysis_details',
]
READ_TABLE_COLUMNS = {'aligned_dna_short_read_id', 'experiment_dna_short_read_id'}
READ_TABLE_COLUMNS.update(READ_TABLE_AIRTABLE_FIELDS)
READ_RNA_TABLE_AIRTABLE_ID_FIELDS = ['aligned_rna_short_read_file', 'aligned_rna_short_read_index_file']
READ_RNA_TABLE_AIRTABLE_FIELDS = [
    'gene_annotation', 'alignment_software', 'alignment_log_file', 'percent_uniquely_aligned', 'percent_multimapped', 'percent_unaligned',
]
READ_RNA_TABLE_COLUMNS = {'aligned_rna_short_read_id', 'experiment_rna_short_read_id'}
READ_RNA_TABLE_COLUMNS.update(READ_RNA_TABLE_AIRTABLE_ID_FIELDS)
READ_RNA_TABLE_COLUMNS.update(READ_RNA_TABLE_AIRTABLE_FIELDS)
READ_RNA_TABLE_COLUMNS.update(READ_TABLE_AIRTABLE_FIELDS[2:-1])
READ_SET_TABLE_COLUMNS = {'aligned_dna_short_read_set_id', 'aligned_dna_short_read_id'}
CALLED_VARIANT_FILE_COLUMN = 'called_variants_dna_file'
CALLED_TABLE_COLUMNS = {
    'called_variants_dna_short_read_id', 'aligned_dna_short_read_set_id', CALLED_VARIANT_FILE_COLUMN, 'md5sum',
    'caller_software', 'variant_types', 'analysis_details',
}
GENETIC_FINDINGS_TABLE_COLUMNS = {
    'chrom', 'pos', 'ref', 'alt', 'variant_type', 'variant_reference_assembly', 'gene', 'transcript', 'hgvsc', 'hgvsp',
    'gene_known_for_phenotype', 'known_condition_name', 'condition_id', 'condition_inheritance', 'phenotype_contribution',
    'genetic_findings_id', 'participant_id', 'experiment_id', 'zygosity', 'allele_balance_or_heteroplasmy_percentage',
    'variant_inheritance', 'linked_variant', 'additional_family_members_with_variant', 'method_of_discovery',
}

RNA_ONLY = EXPERIMENT_RNA_TABLE_AIRTABLE_FIELDS + READ_RNA_TABLE_AIRTABLE_FIELDS + ['reference_assembly_uri']
DATA_TYPE_OMIT = {
    'wgs': ['targeted_regions_method'] + RNA_ONLY, 'wes': RNA_ONLY, 'rna': [
        'targeted_regions_method', 'target_insert_size', 'mean_coverage', 'aligned_dna_short_read_file',
        'aligned_dna_short_read_index_file',
    ],
}
NO_DATA_TYPE_FIELDS = {
    'targeted_region_bed_file', 'reference_assembly', 'analysis_details', 'percent_rRNA', 'percent_mRNA',
    'alignment_software_dna',
}
NO_DATA_TYPE_FIELDS.update(READ_RNA_TABLE_AIRTABLE_ID_FIELDS)

DATA_TYPE_AIRTABLE_COLUMNS = EXPERIMENT_TABLE_AIRTABLE_FIELDS + READ_TABLE_AIRTABLE_FIELDS + RNA_ONLY + [
    COLLABORATOR_SAMPLE_ID_FIELD, SMID_FIELD]
ALL_AIRTABLE_COLUMNS = DATA_TYPE_AIRTABLE_COLUMNS + list(CALLED_TABLE_COLUMNS) + ['experiment_id']
AIRTABLE_QUERY_COLUMNS = set()
AIRTABLE_QUERY_COLUMNS.update(CALLED_TABLE_COLUMNS)
AIRTABLE_QUERY_COLUMNS.remove('md5sum')
AIRTABLE_QUERY_COLUMNS.update(NO_DATA_TYPE_FIELDS)
for data_type in GREGOR_DATA_TYPES:
    data_type_columns = set(DATA_TYPE_AIRTABLE_COLUMNS) - NO_DATA_TYPE_FIELDS - set(DATA_TYPE_OMIT[data_type])
    AIRTABLE_QUERY_COLUMNS.update({f'{field}_{data_type}' for field in data_type_columns})

WARN_MISSING_TABLE_COLUMNS = {
    'participant': ['recontactable',  'reported_race', 'affected_status', 'phenotype_description', 'age_at_enrollment'],
    'genetic_findings': ['known_condition_name'],
}
WARN_MISSING_CONDITIONAL_COLUMNS = {
    'reported_race': lambda row: not row['ancestry_detail'],
    'age_at_enrollment': lambda row: row['affected_status'] == 'Affected',
    'known_condition_name': lambda row: row['condition_id'],
}

SOLVE_STATUS_LOOKUP = {
    **{s: 'Yes' for s in Family.SOLVED_ANALYSIS_STATUSES},
    **{s: 'Likely' for s in Family.STRONG_CANDIDATE_ANALYSIS_STATUSES},
    Family.ANALYSIS_STATUS_PARTIAL_SOLVE: 'Partial',
}
GREGOR_ANCESTRY_DETAIL_MAP = deepcopy(ANCESTRY_DETAIL_MAP)
GREGOR_ANCESTRY_DETAIL_MAP.pop(MIDDLE_EASTERN)
GREGOR_ANCESTRY_DETAIL_MAP.update({
    HISPANIC: 'Other',
    OTHER_POPULATION: 'Other',
})
GREGOR_ANCESTRY_MAP = deepcopy(ANCESTRY_MAP)
GREGOR_ANCESTRY_MAP.update({
    MIDDLE_EASTERN: 'Middle Eastern or North African',
    HISPANIC: None,
    OTHER_POPULATION: None,
})
MIM_INHERITANCE_MAP = {
    'Digenic dominant': 'Digenic',
    'Digenic recessive': 'Digenic',
    'X-linked dominant': 'X-linked',
    'X-linked recessive': 'X-linked',
}
MIM_INHERITANCE_MAP.update({inheritance: 'Other' for inheritance in [
    'Isolated cases', 'Multifactorial', 'Pseudoautosomal dominant', 'Pseudoautosomal recessive', 'Somatic mutation'
]})
ZYGOSITY_MAP = {
    1: 'Heterozygous',
    2: 'Homozygous',
}
MITO_ZYGOSITY_MAP = {
    1: 'Heteroplasmy',
    2: 'Homoplasmy',
}
METHOD_MAP = {
    Sample.SAMPLE_TYPE_WES: 'SR-ES',
    Sample.SAMPLE_TYPE_WGS: 'SR-GS',
}

HPO_QUALIFIERS = {
    'age_of_onset': {
        'Adult onset': 'HP:0003581',
        'Childhood onset': 'HP:0011463',
        'Congenital onset': 'HP:0003577',
        'Embryonal onset': 'HP:0011460',
        'Fetal onset': 'HP:0011461',
        'Infantile onset': 'HP:0003593',
        'Juvenile onset': 'HP:0003621',
        'Late onset': 'HP:0003584',
        'Middle age onset': 'HP:0003596',
        'Neonatal onset': 'HP:0003623',
        'Young adult onset': 'HP:0011462',
    },
    'pace_of_progression': {
        'Nonprogressive': 'HP:0003680',
        'Slow progression': 'HP:0003677',
        'Progressive': 'HP:0003676',
        'Rapidly progressive': 'HP:0003678',
        'Variable progression rate': 'HP:0003682',
    },
    'severity': {
        'Borderline': 'HP:0012827',
        'Mild': 'HP:0012825',
        'Moderate': 'HP:0012826',
        'Severe': 'HP:0012828',
        'Profound': 'HP:0012829',
    },
    'temporal_pattern': {
        'Insidious onset': 'HP:0003587',
        'Chronic': 'HP:0011010',
        'Subacute': 'HP:0011011',
        'Acute': 'HP:0011009',
    },
    'spatial_pattern': {
        'Generalized': 'HP:0012837',
        'Localized': 'HP:0012838',
        'Distal': 'HP:0012839',
        'Proximal': 'HP:0012840',
    },
}


@analyst_required
def gregor_export(request):
    request_json = json.loads(request.body)
    missing_required_fields = [field for field in ['consentCode', 'deliveryPath'] if not request_json.get(field)]
    if missing_required_fields:
        raise ErrorsWarningsException([f'Missing required field(s): {", ".join(missing_required_fields)}'])

    consent_code = request_json['consentCode']
    file_path = request_json['deliveryPath']
    if not is_google_bucket_file_path(file_path):
        raise ErrorsWarningsException(['Delivery Path must be a valid google bucket path (starts with gs://)'])
    if not does_file_exist(file_path, user=request.user):
        raise ErrorsWarningsException(['Invalid Delivery Path: folder not found'])

    projects = get_internal_projects().filter(
        guid__in=get_project_guids_user_can_view(request.user),
        consent_code=consent_code[0],
        projectcategory__name='GREGoR',
    )
    sample_types = Sample.objects.filter(individual__family__project__in=projects).values_list('individual_id', 'sample_type')
    individual_data_types = defaultdict(set)
    for individual_db_id, sample_type in sample_types:
        individual_data_types[individual_db_id].add(sample_type)
    individuals = Individual.objects.filter(id__in=individual_data_types).prefetch_related(
        'family__project', 'mother', 'father')

    grouped_data_type_individuals = defaultdict(dict)
    family_individuals = defaultdict(dict)
    for i in individuals:
        grouped_data_type_individuals[i.individual_id].update({data_type: i for data_type in individual_data_types[i.id]})
        family_individuals[i.family_id][i.guid] = i

    saved_variants_by_family = get_saved_discovery_variants_by_family(
        variant_filter={'family__project__in': projects, 'alt__isnull': False},
        format_variants=_parse_variant_genetic_findings,
        get_family_id=lambda v: v['family_id'],
    )

    airtable_sample_records, airtable_metadata_by_participant = _get_gregor_airtable_data(
        grouped_data_type_individuals.keys(), request.user)

    participant_rows = []
    family_map = {}
    phenotype_rows = []
    analyte_rows = []
    airtable_rows = []
    airtable_rna_rows = []
    experiment_lookup_rows = []
    genetic_findings_rows = []
    for data_type_individuals in grouped_data_type_individuals.values():
        # If multiple individual records, prefer WGS
        individual = next(
            data_type_individuals[data_type.upper()] for data_type in GREGOR_DATA_TYPES
            if data_type_individuals.get(data_type.upper())
        )

        # family table
        family = individual.family
        if family not in family_map:
            family_map[family] = _get_gregor_family_row(family)

        if individual.consanguinity is not None and family_map[family]['consanguinity'] == 'Unknown':
            family_map[family]['consanguinity'] = 'Present' if individual.consanguinity else 'None suspected'

        # participant table
        airtable_sample = airtable_sample_records.get(individual.individual_id, {})
        participant_id = _get_participant_id(individual)
        participant = _get_participant_row(individual, airtable_sample)
        participant.update(family_map[family])
        participant.update({
            'participant_id': participant_id,
            'consent_code': consent_code,
        })
        participant_rows.append(participant)

        # phenotype table
        base_phenotype_row = {'participant_id': participant_id, 'presence': 'Present', 'ontology': 'HPO'}
        phenotype_rows += [
            dict(**base_phenotype_row, **_get_phenotype_row(feature)) for feature in individual.features or []
        ]
        base_phenotype_row['presence'] = 'Absent'
        phenotype_rows += [
            dict(**base_phenotype_row, **_get_phenotype_row(feature)) for feature in individual.absent_features or []
        ]

        analyte_ids = set()
        experiment_id = None
        # airtable data
        if airtable_sample:
            airtable_metadata = airtable_metadata_by_participant.get(airtable_sample[PARTICIPANT_ID_FIELD]) or {}
            for data_type in data_type_individuals:
                if data_type not in airtable_metadata:
                    continue
                row = _get_airtable_row(data_type, airtable_metadata)
                analyte_ids.add(row['analyte_id'])
                is_rna = data_type == 'RNA'
                if not is_rna:
                    row['alignment_software'] = row['alignment_software_dna']
                    experiment_id = row['experiment_dna_short_read_id']
                (airtable_rna_rows if is_rna else airtable_rows).append(row)
                experiment_lookup_rows.append(
                    {'participant_id': participant_id, **_get_experiment_lookup_row(is_rna, row)}
                )

        # analyte table
        if not analyte_ids:
            analyte_id = _get_analyte_id(airtable_sample)
            if analyte_id:
                analyte_ids.add(analyte_id)
        for analyte_id in analyte_ids:
            analyte_rows.append(dict(participant_id=participant_id, analyte_id=analyte_id, **_get_analyte_row(individual)))

        if participant['proband_relationship'] == 'Self':
            genetic_findings_rows += _get_gregor_genetic_findings_rows(
                saved_variants_by_family.get(family.id), individual, participant_id, experiment_id,
                data_type_individuals.keys(), family_individuals[family.id],
            )

    file_data = [
        ('participant', PARTICIPANT_TABLE_COLUMNS, participant_rows),
        ('family', GREGOR_FAMILY_TABLE_COLUMNS, list(family_map.values())),
        ('phenotype', PHENOTYPE_TABLE_COLUMNS, phenotype_rows),
        ('analyte', ANALYTE_TABLE_COLUMNS, analyte_rows),
        ('experiment_dna_short_read', EXPERIMENT_TABLE_COLUMNS, airtable_rows),
        ('aligned_dna_short_read', READ_TABLE_COLUMNS, airtable_rows),
        ('aligned_dna_short_read_set', READ_SET_TABLE_COLUMNS, airtable_rows),
        ('called_variants_dna_short_read', CALLED_TABLE_COLUMNS, [
            row for row in airtable_rows if row.get(CALLED_VARIANT_FILE_COLUMN)
        ]),
        ('experiment_rna_short_read', EXPERIMENT_RNA_TABLE_COLUMNS, airtable_rna_rows),
        ('aligned_rna_short_read', READ_RNA_TABLE_COLUMNS, airtable_rna_rows),
        ('experiment', EXPERIMENT_LOOKUP_TABLE_COLUMNS, experiment_lookup_rows),
        ('genetic_findings', GENETIC_FINDINGS_TABLE_COLUMNS, genetic_findings_rows),
    ]

    files, warnings = _populate_gregor_files(file_data)
    write_multiple_files_to_gs(files, file_path, request.user, file_format='tsv')

    return create_json_response({
        'info': [f'Successfully validated and uploaded Gregor Report for {len(family_map)} families'],
        'warnings': warnings,
    })


def _get_gregor_airtable_data(individual_ids, user):
    sample_records, session = get_airtable_samples(
        individual_ids, user, fields=[SMID_FIELD, PARTICIPANT_ID_FIELD, 'Recontactable'],
    )

    airtable_metadata = session.fetch_records(
        'GREGoR Data Model',
        fields=[PARTICIPANT_ID_FIELD] + sorted(AIRTABLE_QUERY_COLUMNS),
        or_filters={f'{PARTICIPANT_ID_FIELD}': {r[PARTICIPANT_ID_FIELD] for r in sample_records.values()}},
    )

    airtable_metadata_by_participant = {r[PARTICIPANT_ID_FIELD]: r for r in airtable_metadata.values()}
    for data_type in GREGOR_DATA_TYPES:
        for r in airtable_metadata_by_participant.values():
            data_type_fields = [f for f in r if f.endswith(f'_{data_type}')]
            if data_type_fields:
                r[data_type.upper()] = {f.replace(f'_{data_type}', ''): r.pop(f) for f in data_type_fields}

    return sample_records, airtable_metadata_by_participant


def _get_gregor_family_row(family):
    return {
        'family_id':  f'Broad_{family.family_id}',
        'internal_project_id': f'Broad_{family.project.name}',
        'consanguinity': 'Unknown',
        'pmid_id': '|'.join(family.pubmed_ids or []),
        'phenotype_description': family.coded_phenotype,
        'solve_status': SOLVE_STATUS_LOOKUP.get(family.analysis_status, 'No'),
    }


def _get_participant_id(individual):
    return f'Broad_{individual.individual_id}'


def _get_participant_row(individual, airtable_sample):
    participant = {
        'gregor_center': 'BROAD',
        'paternal_id': f'Broad_{individual.father.individual_id}' if individual.father else '0',
        'maternal_id': f'Broad_{individual.mother.individual_id}' if individual.mother else '0',
        'prior_testing': '|'.join([gene.get('gene', gene['comments']) for gene in individual.rejected_genes or []]),
        'proband_relationship': individual.get_proband_relationship_display(),
        'sex': individual.get_sex_display(),
        'affected_status': individual.get_affected_display(),
        'reported_race': GREGOR_ANCESTRY_MAP.get(individual.population),
        'ancestry_detail': GREGOR_ANCESTRY_DETAIL_MAP.get(individual.population),
        'reported_ethnicity': ANCESTRY_MAP[HISPANIC] if individual.population == HISPANIC else None,
        'recontactable': airtable_sample.get('Recontactable'),
        'missing_variant_case': 'No',
    }
    if individual.birth_year and individual.birth_year > 0:
        participant.update({
            'age_at_last_observation': str(datetime.now().year - individual.birth_year),
            'age_at_enrollment': str(individual.created_date.year - individual.birth_year),
        })
    return participant


def _get_phenotype_row(feature):
    qualifiers_by_type = {
        q['type']: HPO_QUALIFIERS[q['type']][q['label']]
        for q in feature.get('qualifiers') or [] if q['type'] in HPO_QUALIFIERS
    }
    onset_age = qualifiers_by_type.pop('age_of_onset', None)
    return {
        'term_id': feature['id'],
        'additional_details': feature.get('notes', '').replace('\r\n', ' ').replace('\n', ' '),
        'onset_age_range': onset_age,
        'additional_modifiers': '|'.join(qualifiers_by_type.values()),
    }


def _parse_variant_genetic_findings(variant_models, *args):
    variant_models = variant_models.annotate(
        omim_numbers=F('family__post_discovery_omim_numbers'),
        mondo_id=F('family__mondo_id'),
    )
    variants = []
    gene_ids = set()
    mim_numbers = set()
    mondo_ids = set()
    for variant in variant_models:
        chrom, pos = get_chrom_pos(variant.xpos)

        main_transcript = _get_variant_model_main_transcript(variant)
        gene_id = main_transcript.get('geneId')
        gene_ids.add(gene_id)

        condition_id = ''
        if variant.omim_numbers:
            mim_number = variant.omim_numbers[0]
            mim_numbers.add(mim_number)
            condition_id = f'OMIM:{mim_number}'
        elif variant.mondo_id:
            condition_id = f"MONDO:{variant.mondo_id.replace('MONDO:', '')}"
            mondo_ids.add(condition_id)

        variants.append({
            'family_id': variant.family_id,
            'chrom': chrom,
            'pos': pos,
            'ref': variant.ref,
            'alt': variant.alt,
            'variant_type': 'SNV/INDEL',
            'variant_reference_assembly': GENOME_VERSION_LOOKUP[variant.saved_variant_json['genomeVersion']],
            'genotypes': variant.saved_variant_json['genotypes'],
            'gene_id': gene_id,
            'transcript': main_transcript.get('transcriptId'),
            'hgvsc': (main_transcript.get('hgvsc') or '').split(':')[-1],
            'hgvsp': (main_transcript.get('hgvsp') or '').split(':')[-1],
            'gene_known_for_phenotype': 'Known' if condition_id else 'Candidate',
            'condition_id': condition_id,
            'phenotype_contribution': 'Full',
        })

    genes_by_id = get_genes(gene_ids)
    conditions_by_id = {
        f'OMIM:{number}':  {
            'known_condition_name': description,
            'condition_inheritance': '|'.join([
                MIM_INHERITANCE_MAP.get(i, i) for i in (inheritance or '').split(', ')
            ]),
        } for number, description, inheritance in Omim.objects.filter(phenotype_mim_number__in=mim_numbers).values_list(
            'phenotype_mim_number', 'phenotype_description', 'phenotype_inheritance',
        )
    }
    conditions_by_id.update({mondo_id: _get_mondo_condition_data(mondo_id) for mondo_id in mondo_ids})
    for row in variants:
        row['gene'] = genes_by_id.get(row['gene_id'], {}).get('geneSymbol')
        row.update(conditions_by_id.get(row['condition_id'], {}))
    return variants


def _get_mondo_condition_data(mondo_id):
    try:
        response = requests.get(f'{MONDO_BASE_URL}/{mondo_id}', timeout=10)
        data = response.json()
        inheritance = data['inheritance']
        if inheritance:
            inheritance = HumanPhenotypeOntology.objects.get(hpo_id=inheritance['id']).name.replace(' inheritance', '')
        return {
            'known_condition_name': data['name'],
            'condition_inheritance': inheritance,
        }
    except Exception:
        return {}


def _get_gregor_genetic_findings_rows(rows, individual, participant_id, experiment_id, individual_data_types, family_individuals):
    parsed_rows = []
    findings_by_gene = defaultdict(list)
    for row in (rows or []):
        genotypes = row['genotypes']
        individual_genotype = genotypes.get(individual.guid)
        if individual_genotype and individual_genotype['numAlt'] > 0:
            heteroplasmy = individual_genotype.get('hl')
            findings_id = f'{participant_id}_{row["chrom"]}_{row["pos"]}'
            findings_by_gene[row['gene']].append(findings_id)
            parsed_rows.append({
                'genetic_findings_id': findings_id,
                'participant_id': participant_id,
                'experiment_id': experiment_id,
                'zygosity': (ZYGOSITY_MAP if heteroplasmy is None else MITO_ZYGOSITY_MAP)[individual_genotype['numAlt']],
                'allele_balance_or_heteroplasmy_percentage': heteroplasmy,
                'variant_inheritance': _get_variant_inheritance(individual, genotypes),
                'additional_family_members_with_variant': '|'.join([
                    f'Broad_{_get_participant_id(family_individuals[guid])}' for guid, g in genotypes.items()
                    if guid != individual.guid and g['numAlt'] > 0
                ]),
                'method_of_discovery': '|'.join([
                    METHOD_MAP.get(data_type) for data_type in individual_data_types if data_type != Sample.SAMPLE_TYPE_RNA
                ]),
                **row,
            })

    for row in parsed_rows:
        gene_findings = findings_by_gene[row['gene']]
        if len(gene_findings) > 1:
            row['linked_variant'] = next(f for f in gene_findings if f != row['genetic_findings_id'])

    return parsed_rows


def _get_variant_inheritance(individual, genotypes):
    parental_inheritance = tuple(
        None if parent is None else genotypes.get(parent.guid, {}).get('numAlt', -1) > 0
        for parent in [individual.mother, individual.father]
    )
    return {
        (True, True): 'biparental',
        (True, False): 'maternal',
        (True, None): 'maternal',
        (False, True): 'paternal',
        (False, False): 'de novo',
        (False, None): 'nonmaternal',
        (None, True): 'paternal',
        (None, False): 'nonpaternal',
        (None, None): 'unknown',
    }[parental_inheritance]


def _get_analyte_row(individual):
    return {
        'analyte_type': individual.get_analyte_type_display(),
        'primary_biosample': individual.get_primary_biosample_display(),
        'tissue_affected_status': 'Yes' if individual.tissue_affected_status else 'No',
    }


def _get_airtable_row(data_type, airtable_metadata):
    data_type_metadata = airtable_metadata[data_type]
    collaborator_sample_id = data_type_metadata[COLLABORATOR_SAMPLE_ID_FIELD]
    experiment_short_read_id = f'Broad_{data_type_metadata.get("experiment_type", "NA")}_{collaborator_sample_id}'
    aligned_short_read_id = f'{experiment_short_read_id}_1'
    return {
        'analyte_id': _get_analyte_id(data_type_metadata),
        'experiment_dna_short_read_id': experiment_short_read_id,
        'experiment_rna_short_read_id': experiment_short_read_id,
        'experiment_sample_id': collaborator_sample_id,
        'aligned_dna_short_read_id': aligned_short_read_id,
        'aligned_rna_short_read_id': aligned_short_read_id,
        **airtable_metadata,
        **data_type_metadata,
    }


def _get_analyte_id(airtable_metadata):
    sm_id = airtable_metadata.get(SMID_FIELD)
    return f'Broad_{sm_id}' if sm_id else None


def _get_experiment_lookup_row(is_rna, row_data):
    table_name = f'experiment_{"rna" if is_rna else "dna"}_short_read'
    id_in_table = row_data[f'{table_name}_id']
    return {
        'table_name': table_name,
        'id_in_table': id_in_table,
        'experiment_id': f'{table_name}.{id_in_table}',
    }

def _validate_enumeration(val, validator):
    delimiter = validator.get('multi_value_delimiter')
    values = val.split(delimiter) if delimiter else [val]
    return all(v in validator['enumerations'] for v in values)

DATA_TYPE_VALIDATORS = {
    'string': lambda val, validator: (not validator.get('is_bucket_path')) or val.startswith('gs://'),
    'enumeration': _validate_enumeration,
    'integer': lambda val, *args: val.isnumeric(),
    'float': lambda val, validator: val.isnumeric() or re.match(r'^\d+.\d+$', val),
    'date': lambda val, validator: bool(re.match(r'^\d{4}-\d{2}-\d{2}$', val)),
}
DATA_TYPE_ERROR_FORMATTERS = {
    'string': lambda validator: ' are a google bucket path starting with gs://',
    'enumeration': lambda validator: f': {", ".join(validator["enumerations"])}',
}
DATA_TYPE_FORMATTERS = {
    'integer': lambda val: str(val).replace(',', ''),
}
DATA_TYPE_FORMATTERS['float'] = DATA_TYPE_FORMATTERS['integer']


def _populate_gregor_files(file_data):
    errors = []
    warnings = []
    try:
        table_configs, required_tables = _load_data_model_validators()
    except Exception as e:
        raise ErrorsWarningsException([f'Unable to load data model: {e}'])

    tables = {f[0] for f in file_data}
    missing_tables = [
        table for table, validator in required_tables.items() if not _has_required_table(table, validator, tables)
    ]
    if missing_tables:
        errors.append(
            f'The following tables are required in the data model but absent from the reports: {", ".join(missing_tables)}'
        )

    files = []
    for file_name, expected_columns, data in file_data:
        table_config = table_configs.get(file_name)
        if not table_config:
            errors.insert(0, f'No data model found for "{file_name}" table')
            continue

        files.append((file_name, list(table_config.keys()), data))

        extra_columns = expected_columns.difference(table_config.keys())
        if extra_columns:
            col_summary = ', '.join(sorted(extra_columns))
            warnings.insert(
                0, f'The following columns are computed for the "{file_name}" table but are missing from the data model: {col_summary}',
            )
        invalid_data_type_columns = {
            col: config['data_type'] for col, config in table_config.items()
            if config.get('data_type') and config['data_type'] not in DATA_TYPE_VALIDATORS
        }
        if invalid_data_type_columns:
            col_summary = ', '.join(sorted([f'{col} ({data_type})' for col, data_type in invalid_data_type_columns.items()]))
            warnings.insert(
                0, f'The following columns are included in the "{file_name}" data model but have an unsupported data type: {col_summary}',
            )
        invalid_enum_columns = [
            col for col, config in table_config.items()
            if config.get('data_type') == 'enumeration' and not config.get('enumerations')
        ]
        if invalid_enum_columns:
            for col in invalid_enum_columns:
                table_config[col]['data_type'] = None
            col_summary = ', '.join(sorted(invalid_enum_columns))
            warnings.insert(
                0, f'The following columns are specified as "enumeration" in the "{file_name}" data model but are missing the allowed values definition: {col_summary}',
            )

        for column, config in table_config.items():
            _validate_column_data(column, file_name, data, column_validator=config, warnings=warnings, errors=errors)

    if errors:
        raise ErrorsWarningsException(errors, warnings)

    return files, warnings


def _load_data_model_validators():
    response = requests.get(GREGOR_DATA_MODEL_URL)
    response.raise_for_status()
    # remove commented out lines from json
    response_json = json.loads(re.sub('\\n\s*//.*\\n', '', response.text))
    table_models = response_json['tables']
    table_configs = {
        t['table']: {c['column']: c for c in t['columns']}
        for t in table_models
    }
    required_tables = {t['table']: _parse_table_required(t['required']) for t in table_models if t.get('required')}
    return table_configs, required_tables


def _parse_table_required(required_validator):
    if required_validator is True:
        return True

    match = re.match(r'CONDITIONAL \(([\w+(\s,)?]+)\)', required_validator)
    return match and match.group(1).split(', ')


def _has_required_table(table, validator, tables):
    if table in tables:
        return True
    if validator is True:
        return False
    return tables.isdisjoint(validator)


def _validate_column_data(column, file_name, data, column_validator, warnings, errors):
    data_type = column_validator.get('data_type')
    data_type_validator = DATA_TYPE_VALIDATORS.get(data_type)
    data_type_formatter = DATA_TYPE_FORMATTERS.get(data_type)
    unique = column_validator.get('is_unique')
    required = column_validator.get('required')
    recommended = column in WARN_MISSING_TABLE_COLUMNS.get(file_name, [])
    if not (required or unique or recommended or data_type_validator):
        return

    missing = []
    warn_missing = []
    invalid = []
    grouped_values = defaultdict(set)
    for row in data:
        value = row.get(column)
        if not value:
            if required:
                missing.append(_get_row_id(row))
            elif recommended:
                check_recommend_condition = WARN_MISSING_CONDITIONAL_COLUMNS.get(column)
                if not check_recommend_condition or check_recommend_condition(row):
                    warn_missing.append(_get_row_id(row))
            continue

        if data_type_formatter:
            value = data_type_formatter(value)
            row[column] = value

        if data_type_validator and not data_type_validator(value, column_validator):
            invalid.append(f'{_get_row_id(row)} ({value})')
        elif unique:
            grouped_values[value].add(_get_row_id(row))

    duplicates = [f'{k} ({", ".join(sorted(v))})' for k, v in grouped_values.items() if len(v) > 1]
    if missing or warn_missing or invalid or duplicates:
        airtable_summary = ' (from Airtable)' if column in ALL_AIRTABLE_COLUMNS else ''
        error_template = f'The following entries {{issue}} "{column}"{airtable_summary} in the "{file_name}" table'
        if missing:
            errors.append(
                f'{error_template.format(issue="are missing required")}: {", ".join(sorted(missing))}'
            )
        if invalid:
            invalid_values = f'Invalid values: {", ".join(sorted(invalid))}'
            allowed = DATA_TYPE_ERROR_FORMATTERS[data_type](column_validator) \
                if data_type in DATA_TYPE_ERROR_FORMATTERS else f' have data type {data_type}'
            errors.append(
                f'{error_template.format(issue="have invalid values for")}. Allowed values{allowed}. {invalid_values}'
            )
        if duplicates:
            errors.append(
                f'{error_template.format(issue="have non-unique values for")}: {", ".join(sorted(duplicates))}'
            )
        if warn_missing:
            warnings.append(
                f'{error_template.format(issue="are missing recommended")}: {", ".join(sorted(warn_missing))}'
            )


def _get_row_id(row):
    id_col = next(col for col in ['participant_id', 'experiment_sample_id', 'family_id'] if col in row)
    return row[id_col]


# Discovery Sheet

# HPO categories are direct children of HP:0000118 "Phenotypic abnormality".
# See https://hpo.jax.org/app/browse/term/HP:0000118
HPO_CATEGORY_DISCOVERY_COLUMNS = {
    'HP:0000478': 'eye_defects',
    'HP:0002664': 'neoplasm',
    'HP:0000818': 'endocrine_system',
    'HP:0000152': 'head_or_neck',
    'HP:0002715': 'immune_system',
    'HP:0001507': 'growth',
    'HP:0045027': 'thoracic_cavity',
    'HP:0001871': 'blood',
    'HP:0002086': 'respiratory',
    'HP:0000598': 'ear_defects',
    'HP:0001939': 'metabolism_homeostasis',
    'HP:0003549': 'connective_tissue',
    'HP:0001608': 'voice',
    'HP:0000707': 'nervous_system',
    'HP:0000769': 'breast',
    'HP:0001197': 'prenatal_development_or_birth',
    'HP:0040064': 'limbs',
    'HP:0025031': 'abdomen',
    'HP:0033127': 'musculature',
    'HP:0001626': 'cardiovascular_system',
    'HP:0000924': 'skeletal_system',
    'HP:0001574': 'integument',
    'HP:0000119': 'genitourinary_system',
}
DISCOVERY_SKIP_HPO_CATEGORIES = {'HP:0025354', 'HP:0025142'}


DEFAULT_ROW = {
    "t0": None,
    "t0_copy": None,
    "months_since_t0": None,
    "sample_source": "CMG",
    "analysis_summary": "",
    "analysis_complete_status": "complete",
    "expected_inheritance_model": "multiple",
    "actual_inheritance_model": "",
    "n_kindreds": "1",
    "gene_name": "NS",
    "novel_mendelian_gene": "NS",
    "gene_count": "NA",
    "phenotype_class": "New",
    "solved": "N",
    "genome_wide_linkage": "NS",
    "p_value": "NS",
    "n_kindreds_overlapping_sv_similar_phenotype": "NS",
    "n_unrelated_kindreds_with_causal_variants_in_gene": "NS",
    "biochemical_function": "NS",
    "protein_interaction": "NS",
    "expression": "NS",
    "patient_cells": "NS",
    "non_patient_cell_model": "NS",
    "animal_model": "NS",
    "non_human_cell_culture_model": "NS",
    "rescue": "NS",
    "omim_number_initial": "NA",
    "omim_number_post_discovery": "NA",
    "submitted_to_mme": "NS",
    "posted_publicly": "NS",
    "komp_early_release": "NS",
}
DEFAULT_ROW.update({hpo_category: 'N' for hpo_category in HPO_CATEGORY_DISCOVERY_COLUMNS.values()})

ADDITIONAL_KINDREDS_FIELD = "n_unrelated_kindreds_with_causal_variants_in_gene"
OVERLAPPING_KINDREDS_FIELD = "n_kindreds_overlapping_sv_similar_phenotype"
FUNCTIONAL_DATA_FIELD_MAP = {
    "Additional Unrelated Kindreds w/ Causal Variants in Gene": ADDITIONAL_KINDREDS_FIELD,
    "Genome-wide Linkage": "genome_wide_linkage",
    "Bonferroni corrected p-value": "p_value",
    "Kindreds w/ Overlapping SV & Similar Phenotype": OVERLAPPING_KINDREDS_FIELD,
    "Biochemical Function": "biochemical_function",
    "Protein Interaction": "protein_interaction",
    "Expression": "expression",
    "Patient Cells": "patient_cells",
    "Non-patient cells": "non_patient_cell_model",
    "Animal Model": "animal_model",
    "Non-human cell culture model": "non_human_cell_culture_model",
    "Rescue": "rescue",
}
METADATA_FUNCTIONAL_DATA_FIELDS = {
    "genome_wide_linkage",
    "p_value",
    OVERLAPPING_KINDREDS_FIELD,
    ADDITIONAL_KINDREDS_FIELD,
}


@analyst_required
def get_category_projects(request, category):
    return create_json_response({
        'projectGuids': list(Project.objects.filter(projectcategory__name__iexact=category).values_list('guid', flat=True)),
    })


@analyst_required
def discovery_sheet(request, project_guid):
    project = Project.objects.filter(guid=project_guid).prefetch_related(
        Prefetch('family_set', to_attr='families', queryset=Family.objects.prefetch_related('individual_set'))
    ).distinct().first()
    if not project:
        message = 'Invalid project {}'.format(project_guid)
        return create_json_response({'error': message}, status = 400, reason = message)
    check_project_permissions(project, request.user)

    rows = []
    errors = []

    loaded_samples_by_family = _get_loaded_samples_by_family(project)
    saved_variants_by_family = _get_project_saved_discovery_variants_by_family(project)
    analysis_notes_by_family = _get_analysis_notes_by_family(project)
    mme_submission_family_guids = _get_has_mme_submission_family_guids([project])

    if not loaded_samples_by_family:
        errors.append("No data loaded for project: {}".format(project))
        return create_json_response({
            'rows': [],
            'errors': errors,
        })

    if "external" in project.name.lower() or "reprocessed" in project.name.lower():
        sequencing_approach = "REAN"
    else:
        sequencing_approach = next(iter(loaded_samples_by_family.values()))[-1].sample_type
    initial_row = {
        "project_guid": project.guid,
        "collaborator": project.name,
        "sequencing_approach": sequencing_approach,
    }
    initial_row.update(DEFAULT_ROW)

    now = timezone.now()
    for family in sorted(project.families, key=lambda family: family.id):
        samples = loaded_samples_by_family.get(family.guid)
        if not samples:
            errors.append("No data loaded for family: %s. Skipping..." % family)
            continue
        saved_variants = saved_variants_by_family.get(family.id)
        analysis_notes = analysis_notes_by_family.get(family.guid)
        submitted_to_mme = family.guid in mme_submission_family_guids

        rows += _generate_rows(initial_row, family, samples, saved_variants, analysis_notes, submitted_to_mme, now=now)

    _update_gene_symbols(rows)
    _update_hpo_categories(rows, errors)
    _update_initial_omim_numbers(rows)

    return create_json_response({
        'rows': rows,
        'errors': errors,
    })


def _get_loaded_samples_by_family(project):
    loaded_samples = Sample.objects.filter(individual__family__project=project).select_related(
        'individual__family').order_by('loaded_date')

    loaded_samples_by_family = defaultdict(list)
    for sample in loaded_samples:
        family = sample.individual.family
        loaded_samples_by_family[family.guid].append(sample)

    return loaded_samples_by_family


def _get_analysis_notes_by_family(project):
    notes = FamilyNote.objects.filter(
        family__project=project, note_type='A').select_related('family').order_by('last_modified_date')

    analysis_notes_by_family = defaultdict(list)
    for note in notes:
        analysis_notes_by_family[note.family.guid].append(note.note)

    return analysis_notes_by_family


def _get_project_saved_discovery_variants_by_family(project):
    return get_saved_discovery_variants_by_family(
        {'family__project': project},
        lambda project_saved_variants, tag_types: project_saved_variants.prefetch_related(
            Prefetch('varianttag_set', to_attr='discovery_tags',
                 queryset=VariantTag.objects.filter(variant_tag_type__in=tag_types).select_related('variant_tag_type'),
            )).prefetch_related('variantfunctionaldata_set'),
        lambda saved_variant: saved_variant.family_id,
    )


def _get_has_mme_submission_family_guids(projects):
    return MatchmakerSubmission.objects.filter(
        individual__family__project__in=projects,
    ).values_list('individual__family__guid', flat=True).distinct()


def _generate_rows(initial_row, family, samples, saved_variants, analysis_notes, submitted_to_mme, now=timezone.now()):
    row = _get_basic_row(initial_row, family, samples, now)
    if submitted_to_mme:
        row["submitted_to_mme"] = "Y"
    if analysis_notes:
        row['analysis_summary'] = '; '.join(analysis_notes)

    individuals = family.individual_set.all()

    expected_inheritance_models = []
    mim_disorders = []
    row['features'] = set()
    for i in individuals:
        expected_inheritance_models += i.expected_inheritance or []
        mim_disorders += i.disorders or []
        row['features'].update([feature['id'] for feature in i.features or []])

    if len(expected_inheritance_models) == 1:
        row["expected_inheritance_model"] = Individual.INHERITANCE_LOOKUP[expected_inheritance_models[0]]

    if mim_disorders:
        row.update({
            "omim_number_initial": mim_disorders[0],
            "phenotype_class": "KNOWN",
        })

    if family.post_discovery_omim_numbers:
        row["omim_number_post_discovery"] = ','.join([str(n) for n in family.post_discovery_omim_numbers])

    if not saved_variants:
        return [row]

    affected_individual_guids = set()
    unaffected_individual_guids = set()
    male_individual_guids = set()
    for sample in samples:
        if sample.individual.affected == "A":
            affected_individual_guids.add(sample.individual.guid)
        elif sample.individual.affected == "N":
            unaffected_individual_guids.add(sample.individual.guid)
        if sample.individual.sex == Individual.SEX_MALE:
            male_individual_guids.add(sample.individual.guid)

    potential_compound_het_genes = defaultdict(set)
    for variant in saved_variants:
        _update_variant_inheritance(
            variant, affected_individual_guids, unaffected_individual_guids, male_individual_guids, potential_compound_het_genes)

    gene_ids_to_saved_variants, gene_ids_to_variant_tag_names, gene_ids_to_inheritance = _get_gene_to_variant_info_map(
        saved_variants, potential_compound_het_genes)

    if len(gene_ids_to_saved_variants) > 1:
        row["gene_count"] = len(gene_ids_to_saved_variants)

    rows = []
    for gene_id, variants in gene_ids_to_saved_variants.items():
        rows.append(_get_gene_row(
            dict(row), gene_id, gene_ids_to_inheritance[gene_id], gene_ids_to_variant_tag_names[gene_id], variants))
    return rows


def _get_basic_row(initial_row, family, samples, now):
    row = {
        "family_guid": family.guid,
        "family_id": family.family_id,
        "extras_pedigree_url": family.pedigree_image.url if family.pedigree_image else "",
        "coded_phenotype": family.coded_phenotype or "",
        "pubmed_ids": '; '.join(family.pubmed_ids),
        "row_id": family.guid,
        "num_individuals_sequenced": len({sample.individual for sample in samples})
    }
    row.update(initial_row)

    t0 = samples[0].loaded_date
    t0_diff = rdelta.relativedelta(now, t0)
    t0_months_since_t0 = t0_diff.years * 12 + t0_diff.months
    row.update({
        "t0": t0,
        "t0_copy": t0,
        "months_since_t0": t0_months_since_t0,
    })
    if t0_months_since_t0 < 12:
        row['analysis_complete_status'] = "first_pass_in_progress"
    return row


def _update_variant_inheritance(variant, affected_individual_guids, unaffected_individual_guids, male_individual_guids, potential_compound_het_genes):
    inheritance_models, potential_compound_het_gene_ids = get_variant_inheritance_models(
        variant.saved_variant_json, affected_individual_guids, unaffected_individual_guids, male_individual_guids)
    variant.saved_variant_json['inheritance'] = inheritance_models

    for gene_id in potential_compound_het_gene_ids:
        potential_compound_het_genes[gene_id].add(variant)

    main_transcript = _get_variant_model_main_transcript(variant)
    if main_transcript.get('geneId'):
        variant.saved_variant_json['mainTranscriptGeneId'] = main_transcript['geneId']


def _get_variant_model_main_transcript(variant):
    variant_json = variant.saved_variant_json
    variant_json['selectedMainTranscriptId'] = variant.selected_main_transcript_id
    return get_variant_main_transcript(variant_json)


def _get_gene_to_variant_info_map(saved_variants, potential_compound_het_genes):
    gene_ids_to_saved_variants = defaultdict(set)
    gene_ids_to_variant_tag_names = defaultdict(set)
    gene_ids_to_inheritance = defaultdict(set)
    # Compound het variants are reported in the gene that they share
    for gene_id, variants in potential_compound_het_genes.items():
        if len(variants) > 1:
            gene_ids_to_inheritance[gene_id].add("AR-comphet")
            # Only include compound hets for one of the genes they are both in
            existing_gene_id = next((
                existing_gene_id for existing_gene_id, existing_variants in gene_ids_to_saved_variants.items()
                if existing_variants == variants), None)
            if existing_gene_id:
                main_gene_ids = {
                    variant.saved_variant_json.get('mainTranscriptGeneId') for variant in variants
                }
                if gene_id in main_gene_ids:
                    gene_ids_to_saved_variants[gene_id] = gene_ids_to_saved_variants[existing_gene_id]
                    del gene_ids_to_saved_variants[existing_gene_id]
                    gene_ids_to_variant_tag_names[gene_id] = gene_ids_to_variant_tag_names[existing_gene_id]
                    del gene_ids_to_variant_tag_names[existing_gene_id]
            else:
                for variant in variants:
                    variant.saved_variant_json['inheritance'] = {"AR-comphet"}
                    gene_ids_to_variant_tag_names[gene_id].update(
                        {vt.variant_tag_type.name for vt in variant.discovery_tags})
                gene_ids_to_saved_variants[gene_id].update(variants)

    # Non-compound het variants are reported in the main transcript gene
    for variant in saved_variants:
        if "AR-comphet" not in variant.saved_variant_json['inheritance']:
            gene_id = variant.saved_variant_json.get('mainTranscriptGeneId')
            if not gene_id and variant.saved_variant_json.get('svType'):
                gene_id = get_sv_name(variant.saved_variant_json)
            gene_ids_to_saved_variants[gene_id].add(variant)
            gene_ids_to_variant_tag_names[gene_id].update({vt.variant_tag_type.name for vt in variant.discovery_tags})
            gene_ids_to_inheritance[gene_id].update(variant.saved_variant_json['inheritance'])

    return gene_ids_to_saved_variants, gene_ids_to_variant_tag_names, gene_ids_to_inheritance


def _get_gene_row(row, gene_id, inheritances, variant_tag_names, variants):
    row["actual_inheritance_model"] = ", ".join(inheritances)

    row["gene_id"] = gene_id
    row["row_id"] += gene_id

    has_tier1 = any(name.startswith("Tier 1") for name in variant_tag_names)
    has_tier2 = any(name.startswith("Tier 2") for name in variant_tag_names)
    has_known_gene_for_phenotype = 'Known gene for phenotype' in variant_tag_names

    row.update({
        "solved": ("TIER 1 GENE" if (has_tier1 or has_known_gene_for_phenotype) else (
            "TIER 2 GENE" if has_tier2 else "N")),
        "komp_early_release": "Y" if 'Share with KOMP' in variant_tag_names else "N",
    })

    if has_tier1 or has_tier2 or has_known_gene_for_phenotype:
        row.update({
            "posted_publicly": "",
            "analysis_complete_status": "complete",
            "novel_mendelian_gene": "Y" if any("Novel gene" in name for name in variant_tag_names) else "N",
        })

    _set_discovery_details(row, variant_tag_names, variants)
    if has_known_gene_for_phenotype:
        row["phenotype_class"] = "KNOWN"
        for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
            row[functional_field] = "KPG"

    if not row["submitted_to_mme"] == 'Y':
        if has_tier1 or has_tier2:
            row["submitted_to_mme"] = "N" if row['months_since_t0'] > 7 else "TBD"
        elif has_known_gene_for_phenotype:
            row["submitted_to_mme"] = "KPG"

    row["extras_variant_tag_list"] = []
    for variant in variants:
        variant_id = variant.saved_variant_json.get('variantId')
        if not variant_id:
            variant_id = "-".join(map(str, list(get_chrom_pos(variant.xpos)) + [variant.ref, variant.alt]))
        row["extras_variant_tag_list"] += [
            (variant_id, gene_id, vt.variant_tag_type.name.lower()) for vt in variant.discovery_tags
        ]
    return row


def _set_discovery_details(row, variant_tag_names, variants):
    phenotype_class = get_discovery_phenotype_class(variant_tag_names)
    if phenotype_class:
        row['phenotype_class'] = phenotype_class

    # Set defaults
    for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
        if functional_field == ADDITIONAL_KINDREDS_FIELD:
            row[functional_field] = "1"
        elif functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
            row[functional_field] = "NA"
        else:
            row[functional_field] = "N"
    # Set values
    for variant in variants:
        for f in variant.variantfunctionaldata_set.all():
            functional_field = FUNCTIONAL_DATA_FIELD_MAP.get(f.functional_data_tag)
            if not functional_field:
                continue
            if functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                value = f.metadata
                if functional_field == ADDITIONAL_KINDREDS_FIELD:
                    value = str(int(value) + 1)
                elif functional_field == OVERLAPPING_KINDREDS_FIELD:
                    value = str(int(value))
                elif row[functional_field] != 'NS':
                    value = '{} {}'.format(row[functional_field], value)
            else:
                value = 'Y'

            row[functional_field] = value


def _update_gene_symbols(rows):
    genes_by_id = get_genes({row['gene_id'] for row in rows if row.get('gene_id')})
    for row in rows:
        if row.get('gene_id'):
            row['gene_name'] = genes_by_id.get(row['gene_id'], {}).get('geneSymbol') or row['gene_id']

        row["extras_variant_tag_list"] = ["{variant_id}  {gene_symbol}  {tag}".format(
            variant_id=variant_id, gene_symbol=genes_by_id.get(gene_id, {}).get('geneSymbol', ''), tag=tag,
        ) for variant_id, gene_id, tag in row.get("extras_variant_tag_list", [])]


def _update_hpo_categories(rows, errors):
    all_features = set()
    for row in rows:
        all_features.update(row['features'])

    hpo_term_to_category = {
        hpo.hpo_id: hpo.category_id for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_features)
    }

    for row in rows:
        category_not_set_on_some_features = False
        for feature in row.pop('features'):
            category = hpo_term_to_category.get(feature)
            if not category:
                category_not_set_on_some_features = True
                continue
            if category in DISCOVERY_SKIP_HPO_CATEGORIES:
                continue

            hpo_category_column_key = HPO_CATEGORY_DISCOVERY_COLUMNS[category]
            row[hpo_category_column_key] = "Y"

        if category_not_set_on_some_features:
            errors.append('HPO category field not set for some HPO terms in {}'.format(row['family_id']))


def _update_initial_omim_numbers(rows):
    omim_numbers = {row['omim_number_initial'] for row in rows if row['omim_number_initial'] and row['omim_number_initial'] != 'NA'}

    omim_number_map = {str(omim.phenotype_mim_number): omim.phenotypic_series_number
                       for omim in Omim.objects.filter(phenotype_mim_number__in=omim_numbers, phenotypic_series_number__isnull=False)}

    for mim_number, phenotypic_series_number in omim_number_map.items():
        logger.info("Will replace OMIM initial # %s with phenotypic series %s" % (mim_number, phenotypic_series_number), user=None)

    for row in rows:
        if omim_number_map.get(row['omim_number_initial']):
            row['omim_number_initial'] = omim_number_map[row['omim_number_initial']]
