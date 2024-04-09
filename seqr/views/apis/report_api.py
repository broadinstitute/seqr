from collections import defaultdict

from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.contrib.postgres.aggregates import ArrayAgg
import json
import re
import requests

from seqr.utils.file_utils import is_google_bucket_file_path, does_file_exist
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException

from seqr.views.utils.airtable_utils import AirtableSession
from seqr.views.utils.anvil_metadata_utils import parse_anvil_metadata, \
    FAMILY_ROW_TYPE, SUBJECT_ROW_TYPE, SAMPLE_ROW_TYPE, DISCOVERY_ROW_TYPE, PARTICIPANT_TABLE, PHENOTYPE_TABLE, \
    EXPERIMENT_TABLE, EXPERIMENT_LOOKUP_TABLE, FINDINGS_TABLE, FINDING_METADATA_COLUMNS
from seqr.views.utils.export_utils import export_multiple_files, write_multiple_files_to_gs
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import analyst_required, get_project_and_check_permissions, \
    get_project_guids_user_can_view, get_internal_projects
from seqr.views.utils.terra_api_utils import anvil_enabled

from seqr.models import Project, Family, Sample, Individual
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
DISCOVERY_TABLE_COLUMNS = [
    'entity:discovery_id', 'subject_id', 'sample_id', 'Gene', 'Gene_Class', 'inheritance_description', 'Zygosity',
    'variant_genome_build', 'Chrom', 'Pos', 'Ref', 'Alt', 'hgvsc', 'hgvsp', 'Transcript', 'sv_name', 'sv_type',
    'significance', 'discovery_notes',
]

PHENOTYPE_PROJECT_CATEGORIES = [
    'Muscle', 'Eye', 'Renal', 'Neuromuscular', 'IBD', 'Epilepsy', 'Orphan', 'Hematologic',
    'Disorders of Sex Development', 'Delayed Puberty', 'Neurodevelopmental', 'Stillbirth', 'ROHHAD', 'Microtia',
    'Diabetes', 'Mitochondrial', 'Cardiovascular',
]


@analyst_required
def anvil_export(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    parsed_rows = defaultdict(list)

    def _add_row(row, family_id, row_type):
        if row_type == DISCOVERY_ROW_TYPE:
            missing_gene_rows = [
                '{chrom}-{pos}-{ref}-{alt}'.format(**discovery_row) for discovery_row in row
                if not (discovery_row.get('gene_id') or discovery_row.get('svType'))]
            if missing_gene_rows:
                raise ErrorsWarningsException(
                    [f'Discovery variant(s) {", ".join(missing_gene_rows)} in family {family_id} have no associated gene'])
            parsed_rows[row_type] += [{
                'entity:discovery_id': f'{discovery_row["chrom"]}_{discovery_row["pos"]}_{discovery_row["participant_id"]}',
                **{k: str(discovery_row.get(k.lower()) or '') for k in ['Gene', 'Zygosity', 'Chrom', 'Pos', 'Ref', 'Alt', 'Transcript']},
                **{k: discovery_row[field] for k, field in {
                    'subject_id': 'participant_id',
                    'Gene_Class': 'gene_known_for_phenotype',
                    'inheritance_description': 'variant_inheritance',
                    'variant_genome_build': 'variant_reference_assembly',
                    'sv_type': 'svType',
                    'discovery_notes': 'notes',
                }.items()},
                **discovery_row,
            } for discovery_row in row]
        else:
            if 'participant_id' in row:
                row['subject_id'] = row['participant_id']
            id_field = f'{row_type}_id'
            entity_id_field = f'entity:{id_field}'
            if id_field in row and entity_id_field not in row:
                row[entity_id_field] = row[id_field]
            if row_type == SUBJECT_ROW_TYPE:
                row.update({
                    'project_id': row.pop('internal_project_id'),
                    'solve_state': row.pop('solve_status'),
                    'disease_id': row.get('condition_id', '').replace('|', ';'),
                    'disease_description': row.get('known_condition_name', '').replace('|', ';'),
                    'hpo_present': '|'.join([feature['id'] for feature in row.get('features') or []]),
                    'hpo_absent': '|'.join([feature['id'] for feature in row.get('absent_features') or []]),
                    'ancestry': row['reported_ethnicity'] or row['reported_race'],
                })
            parsed_rows[row_type].append(row)

    max_loaded_date = request.GET.get('loadedBefore') or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    parse_anvil_metadata(
        [project], request.user, _add_row, max_loaded_date=max_loaded_date, include_discovery_sample_id=True,
        get_additional_individual_fields=lambda individual, *args: {
            'congenital_status': Individual.ONSET_AGE_LOOKUP[individual.onset_age] if individual.onset_age else 'Unknown',
        },
        get_additional_sample_fields=lambda sample, *args: {
            'entity:sample_id': sample.individual.individual_id,
            'sequencing_center': 'Broad',
        },
        family_fields={'phenotype_group': {
            'value': ArrayAgg(
                'project__projectcategory__name', distinct=True,
                filter=Q(project__projectcategory__name__in=PHENOTYPE_PROJECT_CATEGORIES),
            ),
            'format': lambda f: '|'.join(f.pop('phenotype_group')),
        }},
    )

    return export_multiple_files([
        ['{}_PI_Subject'.format(project.name), SUBJECT_TABLE_COLUMNS, parsed_rows[SUBJECT_ROW_TYPE]],
        ['{}_PI_Sample'.format(project.name), SAMPLE_TABLE_COLUMNS, parsed_rows[SAMPLE_ROW_TYPE]],
        ['{}_PI_Family'.format(project.name), FAMILY_TABLE_COLUMNS, parsed_rows[FAMILY_ROW_TYPE]],
        ['{}_PI_Discovery'.format(project.name), DISCOVERY_TABLE_COLUMNS, parsed_rows[DISCOVERY_ROW_TYPE]],
    ], '{}_AnVIL_Metadata'.format(project.name), add_header_prefix=True, file_format='tsv', blank_value='-')


# GREGoR metadata

GREGOR_CATEGORY = 'GREGoR'
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
    *FINDING_METADATA_COLUMNS[:4], 'phenotype_contribution',
    'genetic_findings_id', 'participant_id', 'experiment_id', 'zygosity', 'allele_balance_or_heteroplasmy_percentage',
    'variant_inheritance', 'linked_variant', 'additional_family_members_with_variant', 'method_of_discovery',
}

RNA_ONLY = EXPERIMENT_RNA_TABLE_AIRTABLE_FIELDS + READ_RNA_TABLE_AIRTABLE_FIELDS + [
    'reference_assembly_uri', 'tissue_affected_status', 'Primary_Biosample']
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
    PARTICIPANT_TABLE: ['recontactable',  'reported_race', 'affected_status', 'phenotype_description', 'age_at_enrollment'],
    FINDINGS_TABLE: ['known_condition_name'],
}
WARN_MISSING_CONDITIONAL_COLUMNS = {
    'reported_race': lambda row: not row['ancestry_detail'],
    'age_at_enrollment': lambda row: row['affected_status'] == 'Affected',
    'known_condition_name': lambda row: row.get('condition_id'),
}

INDIVIDUAL_BIOSAMPLE_LOOKUP = dict(Individual.BIOSAMPLE_CHOICES)
BIOSAMPLE_LOOKUP = {k: INDIVIDUAL_BIOSAMPLE_LOOKUP[v] for k, v in {
    'Tissue': 'T',
    'Saliva': 'S',
    'Skin': 'SE',
    'Skin Epidermis': 'SE',
    'Brain Tissue': 'NT',
    'Muscle': 'MT',
    'Blood': 'WB',
    'Buccal': 'BM',
    'Nasal Epithelium': 'NE',
}.items()}
BIOSAMPLE_LOOKUP['Fibroblast'] = 'CL: 0000057'

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
        projectcategory__name=GREGOR_CATEGORY,
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
        participant_id = _format_gregor_id(i.individual_id)
        grouped_data_type_individuals[participant_id].update({data_type: i for data_type in individual_data_types[i.id]})
        family_individuals[i.family_id][i.guid] = participant_id

    # If multiple individual records, prefer WGS
    individual_lookup = {
        next(data_type_individuals[data_type.upper()] for data_type in GREGOR_DATA_TYPES
             if data_type_individuals.get(data_type.upper())): None
        for data_type_individuals in grouped_data_type_individuals.values()
    }

    participant_rows = []
    family_map = {}
    genetic_findings_rows = []

    def _add_row(row, family_id, row_type):
        if row_type == FAMILY_ROW_TYPE:
            family_map[family_id] = row
        elif row_type == SUBJECT_ROW_TYPE:
            participant_rows.append({**row, 'consent_code': consent_code})
        elif row_type == DISCOVERY_ROW_TYPE and row:
            for variant in row:
                genetic_findings_rows.append({
                    **variant, 'phenotype_contribution': 'Full', 'variant_type': 'SNV/INDEL',
                })

    parse_anvil_metadata(
        projects,
        user=request.user,
        individual_samples=individual_lookup,
        individual_data_types=grouped_data_type_individuals,
        add_row=_add_row,
        format_id=_format_gregor_id,
        get_additional_individual_fields=_get_participant_row,
        post_process_variant=_post_process_gregor_variant,
        variant_filter={'alt__isnull': False},
        airtable_fields=[SMID_FIELD, PARTICIPANT_ID_FIELD, 'Recontactable'],
        include_mondo=True,
        proband_only_variants=True,
    )

    airtable_metadata_by_participant = _get_gregor_airtable_data(participant_rows, request.user)

    phenotype_rows = []
    analyte_rows = []
    airtable_rows = []
    airtable_rna_rows = []
    experiment_lookup_rows = []
    experiment_ids_by_participant = {}
    for participant in participant_rows:
        # phenotype table
        base_phenotype_row = {'participant_id': participant['participant_id'], 'presence': 'Present', 'ontology': 'HPO'}
        phenotype_rows += [
            dict(**base_phenotype_row, **_get_phenotype_row(feature)) for feature in participant['features'] or []
        ]
        base_phenotype_row['presence'] = 'Absent'
        phenotype_rows += [
            dict(**base_phenotype_row, **_get_phenotype_row(feature)) for feature in participant['absent_features'] or []
        ]

        if not participant[PARTICIPANT_ID_FIELD]:
            continue

        airtable_metadata = airtable_metadata_by_participant.get(participant[PARTICIPANT_ID_FIELD]) or {}

        has_analyte = False
        # airtable data
        for data_type in grouped_data_type_individuals[participant['participant_id']]:
            if data_type not in airtable_metadata:
                continue
            is_rna, row = _get_airtable_row(data_type, airtable_metadata)
            has_analyte = True
            analyte_rows.append({**participant, **row})
            if not is_rna:
                experiment_ids_by_participant[participant['participant_id']] = row['experiment_dna_short_read_id']
            (airtable_rna_rows if is_rna else airtable_rows).append(row)
            experiment_lookup_rows.append(
                {'participant_id': participant['participant_id'], **_get_experiment_lookup_row(is_rna, row)}
            )

        if participant['analyte_id'] and not has_analyte:
            analyte_rows.append(participant)

    # Add experiment IDs
    for variant in genetic_findings_rows:
        variant['experiment_id'] = experiment_ids_by_participant.get(variant['participant_id'])

    file_data = [
        (PARTICIPANT_TABLE, PARTICIPANT_TABLE_COLUMNS, participant_rows),
        ('family', GREGOR_FAMILY_TABLE_COLUMNS, list(family_map.values())),
        (PHENOTYPE_TABLE, PHENOTYPE_TABLE_COLUMNS, phenotype_rows),
        ('analyte', ANALYTE_TABLE_COLUMNS, analyte_rows),
        (EXPERIMENT_TABLE, EXPERIMENT_TABLE_COLUMNS, airtable_rows),
        ('aligned_dna_short_read', READ_TABLE_COLUMNS, airtable_rows),
        ('aligned_dna_short_read_set', READ_SET_TABLE_COLUMNS, airtable_rows),
        ('called_variants_dna_short_read', CALLED_TABLE_COLUMNS, [
            row for row in airtable_rows if row.get(CALLED_VARIANT_FILE_COLUMN)
        ]),
        ('experiment_rna_short_read', EXPERIMENT_RNA_TABLE_COLUMNS, airtable_rna_rows),
        ('aligned_rna_short_read', READ_RNA_TABLE_COLUMNS, airtable_rna_rows),
        (EXPERIMENT_LOOKUP_TABLE, EXPERIMENT_LOOKUP_TABLE_COLUMNS, experiment_lookup_rows),
        (FINDINGS_TABLE, GENETIC_FINDINGS_TABLE_COLUMNS, genetic_findings_rows),
    ]

    files, warnings = _populate_gregor_files(file_data)
    write_multiple_files_to_gs(files, file_path, request.user, file_format='tsv')

    return create_json_response({
        'info': [f'Successfully validated and uploaded Gregor Report for {len(family_map)} families'],
        'warnings': warnings,
    })


def _get_gregor_airtable_data(participants, user):
    session = AirtableSession(user)

    airtable_metadata = session.fetch_records(
        'GREGoR Data Model',
        fields=[PARTICIPANT_ID_FIELD] + sorted(AIRTABLE_QUERY_COLUMNS),
        or_filters={f'{PARTICIPANT_ID_FIELD}': {r[PARTICIPANT_ID_FIELD] for r in participants if r[PARTICIPANT_ID_FIELD]}},
    )

    airtable_metadata_by_participant = {r[PARTICIPANT_ID_FIELD]: r for r in airtable_metadata.values()}
    for data_type in GREGOR_DATA_TYPES:
        for r in airtable_metadata_by_participant.values():
            data_type_fields = [f for f in r if f.endswith(f'_{data_type}')]
            if data_type_fields:
                r[data_type.upper()] = {f.replace(f'_{data_type}', ''): r.pop(f) for f in data_type_fields}

    return airtable_metadata_by_participant


def _get_participant_row(individual, airtable_sample):
    participant = {
        'gregor_center': 'BROAD',
        'prior_testing': '|'.join([gene.get('gene', gene['comments']) for gene in individual.rejected_genes or []]),
        'recontactable': (airtable_sample or {}).get('Recontactable'),
        'missing_variant_case': 'No',
        PARTICIPANT_ID_FIELD: (airtable_sample or {}).get(PARTICIPANT_ID_FIELD),
        'analyte_id': _get_analyte_id(airtable_sample or {}),
        'analyte_type': individual.get_analyte_type_display(),
        'primary_biosample': individual.get_primary_biosample_display(),
        'tissue_affected_status': 'Yes' if individual.tissue_affected_status else 'No',
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


def _post_process_gregor_variant(row, gene_variants, **kwargs):
    return {'linked_variant': next(
        v['genetic_findings_id'] for v in gene_variants if v['genetic_findings_id'] != row['genetic_findings_id']
    ) if len(gene_variants) > 1 else None}


def _get_airtable_row(data_type, airtable_metadata):
    data_type_metadata = airtable_metadata[data_type]
    collaborator_sample_id = data_type_metadata[COLLABORATOR_SAMPLE_ID_FIELD]
    experiment_short_read_id = f'Broad_{data_type_metadata.get("experiment_type", "NA")}_{collaborator_sample_id}'
    aligned_short_read_id = f'{experiment_short_read_id}_1'
    row = {
        'analyte_id': _get_analyte_id(data_type_metadata),
        'experiment_dna_short_read_id': experiment_short_read_id,
        'experiment_rna_short_read_id': experiment_short_read_id,
        'experiment_sample_id': collaborator_sample_id,
        'aligned_dna_short_read_id': aligned_short_read_id,
        'aligned_rna_short_read_id': aligned_short_read_id,
        **airtable_metadata,
        **data_type_metadata,
    }
    is_rna = data_type == 'RNA'
    if is_rna:
        biosamples = row.get('Primary_Biosample') or [None]
        row.update({
            'analyte_type': 'RNA',
            'primary_biosample': next((BIOSAMPLE_LOOKUP[b] for b in biosamples if b in BIOSAMPLE_LOOKUP), biosamples[0]),
        })
    else:
        row['alignment_software'] = row['alignment_software_dna']
    return is_rna, row


def _format_gregor_id(id_string, default='0'):
    return f'Broad_{id_string}' if id_string else '0'


def _get_analyte_id(airtable_metadata):
    return _format_gregor_id(airtable_metadata.get(SMID_FIELD), default=None)


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


def _is_required_col(required_validator, row):
    if not required_validator:
        return False

    if required_validator is True:
        return True

    match = re.match(r'CONDITIONAL \(([\w+(\s)?]+) = ([\w+(\s)?]+)\)', required_validator)
    if not match:
        return True

    field, value = match.groups()
    return row[field] == value





def _validate_column_data(column, file_name, data, column_validator, warnings, errors):
    data_type = column_validator.get('data_type')
    data_type_validator = DATA_TYPE_VALIDATORS.get(data_type)
    data_type_formatter = DATA_TYPE_FORMATTERS.get(data_type)
    unique = column_validator.get('is_unique') or column_validator.get('primary_key')
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
            if _is_required_col(required, row):
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
    id_col = next(col for col in ['genetic_findings_id', 'participant_id', 'experiment_sample_id', 'family_id'] if col in row)
    return row[id_col]
