from collections import defaultdict
from copy import deepcopy

from datetime import datetime, timedelta
from dateutil import relativedelta as rdelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Prefetch, Count, F, Q, Value, CharField
from django.db.models.functions import Replace, JSONObject
from django.utils import timezone
import json
import requests

from seqr.utils.file_utils import is_google_bucket_file_path, does_file_exist
from seqr.utils.gene_utils import get_genes
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_search_samples
from seqr.utils.xpos_utils import get_chrom_pos

from seqr.views.utils.airtable_utils import AirtableSession
from seqr.views.utils.export_utils import export_multiple_files, write_multiple_files_to_gs
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.permissions_utils import analyst_required, get_project_and_check_permissions, \
    check_project_permissions, get_project_guids_user_can_view, get_internal_projects
from seqr.views.utils.terra_api_utils import anvil_enabled

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant, Individual, FamilyNote
from reference_data.models import Omim, HumanPhenotypeOntology
from settings import GREGOR_DATA_MODEL_URL


logger = SeqrLogger(__name__)

HET = 'Heterozygous'
HOM_ALT = 'Homozygous'
HEMI = 'Hemizygous'


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
DISCOVERY_TABLE_CORE_COLUMNS = ['entity:discovery_id', 'subject_id', 'sample_id']
DISCOVERY_TABLE_VARIANT_COLUMNS = [
    'Gene', 'Gene_Class', 'inheritance_description', 'Zygosity', 'variant_genome_build', 'Chrom', 'Pos', 'Ref',
    'Alt', 'hgvsc', 'hgvsp', 'Transcript', 'sv_name', 'sv_type', 'significance', 'discovery_notes',
]
DISCOVERY_TABLE_METADATA_VARIANT_COLUMNS = DISCOVERY_TABLE_VARIANT_COLUMNS + [
    'novel_mendelian_gene', 'phenotype_class']

PHENOTYPE_PROJECT_CATEGORIES = [
    'Muscle', 'Eye', 'Renal', 'Neuromuscular', 'IBD', 'Epilepsy', 'Orphan', 'Hematologic',
    'Disorders of Sex Development', 'Delayed Puberty', 'Neurodevelopmental', 'Stillbirth', 'ROHHAD', 'Microtia',
    'Diabetes', 'Mitochondrial', 'Cardiovascular',
]

HISPANIC = 'AMR'
MIDDLE_EASTERN = 'MDE'
OTHER_POPULATION = 'OTH'
ANCESTRY_MAP = {
  'AFR': 'Black or African American',
  HISPANIC: 'Hispanic or Latino',
  'ASJ': 'White',
  'EAS': 'Asian',
  'FIN': 'White',
  MIDDLE_EASTERN: 'Other',
  'NFE': 'White',
  OTHER_POPULATION: 'Other',
  'SAS': 'Asian',
}
ANCESTRY_DETAIL_MAP = {
  'ASJ': 'Ashkenazi Jewish',
  'EAS': 'East Asian',
  'FIN': 'Finnish',
  MIDDLE_EASTERN: 'Middle Eastern',
  'SAS': 'South Asian',
}

INHERITANCE_MODE_MAP = {
    'X-linked': 'X - linked',
    'AR-homozygote': 'Autosomal recessive (homozygous)',
    'AR-comphet': 'Autosomal recessive (compound heterozygous)',
    'de novo': 'de novo',
    'AD': 'Autosomal dominant',
}

GENOME_BUILD_MAP = {
    '37': 'GRCh37',
    '38': 'GRCh38.p12',
}

SV_TYPE_MAP = {
    'DUP': 'Duplication',
    'DEL': 'Deletion',
}

MULTIPLE_DATASET_PRODUCTS = {
    'G4L WES + Array v1',
    'G4L WES + Array v2',
    'Standard Exome Plus GWAS Supplement Array',
    'Standard Germline Exome v5 Plus GSA Array',
    'Standard Germline Exome v5 Plus GWAS Supplement Array',
    'Standard Germline Exome v6 Plus GSA Array',
}


@analyst_required
def anvil_export(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    individual_samples = _get_loaded_before_date_project_individual_samples(
        [project], request.GET.get('loadedBefore'),
    )

    subject_rows, sample_rows, family_rows, discovery_rows = _parse_anvil_metadata(
        individual_samples, request.user, include_collaborator=False)

    # Flatten lists of discovery rows so there is one row per variant
    discovery_rows = [row for row_group in discovery_rows for row in row_group if row]

    return export_multiple_files([
        ['{}_PI_Subject'.format(project.name), SUBJECT_TABLE_COLUMNS, subject_rows],
        ['{}_PI_Sample'.format(project.name), SAMPLE_TABLE_COLUMNS, sample_rows],
        ['{}_PI_Family'.format(project.name), FAMILY_TABLE_COLUMNS, family_rows],
        ['{}_PI_Discovery'.format(project.name), DISCOVERY_TABLE_CORE_COLUMNS + DISCOVERY_TABLE_VARIANT_COLUMNS, discovery_rows],
    ], '{}_AnVIL_Metadata'.format(project.name), add_header_prefix=True, file_format='tsv', blank_value='-')


@analyst_required
def sample_metadata_export(request, project_guid):
    is_all_projects = project_guid == 'all'
    omit_airtable = is_all_projects or 'true' in request.GET.get('omitAirtable', '')
    if is_all_projects:
        projects = get_internal_projects()
    else:
        projects = [get_project_and_check_permissions(project_guid, request.user)]

    mme_family_guids = _get_has_mme_submission_family_guids(projects)

    individual_samples = _get_loaded_before_date_project_individual_samples(
        projects, request.GET.get('loadedBefore') or datetime.now().strftime('%Y-%m-%d'))
    subject_rows, sample_rows, family_rows, discovery_rows = _parse_anvil_metadata(
        individual_samples, request.user, include_collaborator=True, omit_airtable=omit_airtable,
    )
    family_rows_by_id = {row['family_id']: row for row in family_rows}

    rows_by_subject_id = {row['subject_id']: row for row in subject_rows}
    for row in sample_rows:
        rows_by_subject_id[row['subject_id']].update(row)

    for rows in discovery_rows:
        for i, row in enumerate(rows):
            if row:
                parsed_row = {k: row[k] for k in DISCOVERY_TABLE_CORE_COLUMNS}
                parsed_row.update({
                    '{}-{}'.format(k, i + 1): row[k] for k in DISCOVERY_TABLE_METADATA_VARIANT_COLUMNS if row.get(k)
                })
                rows_by_subject_id[row['subject_id']].update(parsed_row)

    rows = list(rows_by_subject_id.values())
    all_features = set()
    for row in rows:
        row.update(family_rows_by_id[row['family_id']])
        row['MME'] = 'Y' if row['family_guid'] in mme_family_guids else 'N'
        if row['ancestry_detail']:
            row['ancestry'] = row['ancestry_detail']
        all_features.update(row['hpo_present'].split('|'))
        all_features.update(row['hpo_absent'].split('|'))

    hpo_name_map = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_features)}
    for row in rows:
        for hpo_key in ['hpo_present', 'hpo_absent']:
            if row[hpo_key]:
                row[hpo_key] = '|'.join(['{} ({})'.format(feature_id, hpo_name_map.get(feature_id, '')) for feature_id in row[hpo_key].split('|')])

    return create_json_response({'rows': rows})


def _parse_anvil_metadata(individual_samples, user, include_collaborator=False, omit_airtable=False):
    family_data = Family.objects.filter(individual__in=individual_samples).distinct().values(
        'id', 'family_id', 'post_discovery_omim_number', 'project__name',
        family_guid=F('guid'),
        pmid_id=Replace('pubmed_ids__0', Value('PMID:'), Value(''), output_field=CharField()),
        phenotype_description=Replace(
            Replace('coded_phenotype', Value(','), Value(';'), output_field=CharField()),
            Value('\t'), Value(' '),
        ),
        project_guid=F('project__guid'),
        genome_version=F('project__genome_version'),
        phenotype_groups=ArrayAgg(
            'project__projectcategory__name', distinct=True,
            filter=Q(project__projectcategory__name__in=PHENOTYPE_PROJECT_CATEGORIES),
        ),
    )

    family_data_by_id = {}
    for f in family_data:
        family_id = f.pop('id')
        f.update({
            'project_id': f.pop('project__name'),
            'phenotype_group': '|'.join(f.pop('phenotype_groups')),
        })
        family_data_by_id[family_id] = f

    samples_by_family_id = defaultdict(list)
    individual_id_map = {}
    sample_ids = set()
    for individual, sample in individual_samples.items():
        samples_by_family_id[individual.family_id].append(sample)
        individual_id_map[individual.id] = individual.individual_id
        sample_ids.add(sample.sample_id)

    family_individual_affected_guids = {}
    for family_id, family_samples in samples_by_family_id.items():
        family_individual_affected_guids[family_id] = (
            {s.individual.guid for s in family_samples if s.individual.affected == Individual.AFFECTED_STATUS_AFFECTED},
            {s.individual.guid for s in family_samples if s.individual.affected == Individual.AFFECTED_STATUS_UNAFFECTED},
            {s.individual.guid for s in family_samples if s.individual.sex == Individual.SEX_MALE},
        )

    sample_airtable_metadata = None if omit_airtable else _get_sample_airtable_metadata(
        list(sample_ids), user, include_collaborator=include_collaborator)

    saved_variants_by_family = _get_parsed_saved_discovery_variants_by_family(list(samples_by_family_id.keys()))
    compound_het_gene_id_by_family, gene_ids = _process_saved_variants(
        saved_variants_by_family, family_individual_affected_guids)
    genes_by_id = get_genes(gene_ids)

    mim_numbers = set()
    for family in family_data:
        if family['post_discovery_omim_number']:
            mim_numbers.update(family['post_discovery_omim_number'].split(','))
    mim_decription_map = {
        str(o.phenotype_mim_number): o.phenotype_description
        for o in Omim.objects.filter(phenotype_mim_number__in=mim_numbers)
    }

    subject_rows = []
    sample_rows = []
    family_rows = []
    discovery_rows = []
    for family_id, family_samples in samples_by_family_id.items():
        saved_variants = saved_variants_by_family[family_id]

        family_subject_row = family_data_by_id[family_id]
        family_subject_row['num_saved_variants'] = len(saved_variants)
        genome_version = family_subject_row.pop('genome_version')

        post_discovery_omim_number = family_subject_row.pop('post_discovery_omim_number')
        if post_discovery_omim_number:
            mim_numbers = post_discovery_omim_number.split(',')
            family_subject_row.update({
                'disease_id': ';'.join(['OMIM:{}'.format(mim_number) for mim_number in mim_numbers]),
                'disease_description': ';'.join([
                    mim_decription_map.get(mim_number, '') for mim_number in mim_numbers]).replace(',', ';'),
            })

        affected_individual_guids, _, male_individual_guids = family_individual_affected_guids[family_id]

        family_consanguinity = any(sample.individual.consanguinity is True for sample in family_samples)
        family_row = {
            'entity:family_id': family_subject_row['family_id'],
            'family_id': family_subject_row['family_id'],
            'consanguinity': 'Present' if family_consanguinity else 'None suspected',
        }
        if len(affected_individual_guids) > 1:
            family_row['family_history'] = 'Yes'
        family_rows.append(family_row)

        parsed_variants = [
            _parse_anvil_family_saved_variant(
                variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id)
            for variant in saved_variants]

        for sample in family_samples:
            individual = sample.individual

            airtable_metadata = None
            has_dbgap_submission = None
            if sample_airtable_metadata is not None:
                airtable_metadata = sample_airtable_metadata.get(sample.sample_id, {})
                dbgap_submission = airtable_metadata.get('dbgap_submission') or set()
                has_dbgap_submission = sample.sample_type in dbgap_submission

            subject_row = _get_subject_row(
                individual, has_dbgap_submission, airtable_metadata, parsed_variants, individual_id_map)
            subject_row.update(family_subject_row)
            subject_rows.append(subject_row)

            sample_row = _get_sample_row(sample, has_dbgap_submission, airtable_metadata)
            sample_rows.append(sample_row)

            discovery_row = _get_discovery_rows(sample, parsed_variants, male_individual_guids)
            discovery_rows.append(discovery_row)

    return subject_rows, sample_rows, family_rows, discovery_rows


def _get_variant_main_transcript(variant):
    main_transcript_id = variant.get('selectedMainTranscriptId') or variant.get('mainTranscriptId')
    if main_transcript_id:
        for gene_id, transcripts in variant.get('transcripts', {}).items():
            main_transcript = next((t for t in transcripts if t['transcriptId'] == main_transcript_id), None)
            if main_transcript:
                if 'geneId' not in main_transcript:
                    main_transcript['geneId'] = gene_id
                return main_transcript
    elif len(variant.get('transcripts', {})) == 1:
        gene_id = next(k for k in variant['transcripts'].keys())
        #  Handle manually created SNPs
        if variant['transcripts'][gene_id] == []:
            return {'geneId': gene_id}
    return {}


def _get_sv_name(variant_json):
    return variant_json.get('svName') or '{svType}:chr{chrom}:{pos}-{end}'.format(**variant_json)


def _get_nested_variant_name(variant):
    return _get_sv_name(variant) if variant.get('svType') else variant['variantId']


def _get_loaded_before_date_project_individual_samples(projects, max_loaded_date):
    if max_loaded_date:
        max_loaded_date = datetime.strptime(max_loaded_date, '%Y-%m-%d')
    else:
        max_loaded_date = datetime.now() - timedelta(days=365)

    loaded_samples = get_search_samples(projects, active_only=False).select_related('individual').order_by('-loaded_date')
    if max_loaded_date:
        loaded_samples = loaded_samples.filter(loaded_date__lte=max_loaded_date)
    #  Only return the oldest sample for each individual
    return {sample.individual: sample for sample in loaded_samples}


def _process_saved_variants(saved_variants_by_family, family_individual_affected_guids):
    gene_ids = set()
    compound_het_gene_id_by_family = {}
    for family_id, saved_variants in saved_variants_by_family.items():
        potential_com_het_gene_variants = defaultdict(list)
        potential_mnvs = defaultdict(list)
        for variant in saved_variants:
            variant['main_transcript'] = _get_variant_main_transcript(variant)
            if variant['main_transcript']:
                gene_ids.add(variant['main_transcript']['geneId'])

            affected_individual_guids, unaffected_individual_guids, male_individual_guids = family_individual_affected_guids[family_id]
            inheritance_models, potential_compound_het_gene_ids = _get_inheritance_models(
                variant, affected_individual_guids, unaffected_individual_guids, male_individual_guids)
            variant['inheritance_models'] = inheritance_models
            for gene_id in potential_compound_het_gene_ids:
                potential_com_het_gene_variants[gene_id].append(variant)
            for guid in variant['discovery_tag_guids_by_name'].values():
                potential_mnvs[guid].append(variant)

        mnv_genes = _process_mnvs(potential_mnvs, saved_variants)
        compound_het_gene_id_by_family.update(
            _process_comp_hets(family_id, potential_com_het_gene_variants, gene_ids, mnv_genes)
        )

    return compound_het_gene_id_by_family, gene_ids


def _process_mnvs(potential_mnvs, saved_variants):
    mnv_genes = set()
    for mnvs in potential_mnvs.values():
        if len(mnvs) <= 2:
            continue
        parent_mnv = next((v for v in mnvs if not v.get('populations')), mnvs[0])
        nested_mnvs = [v for v in mnvs if v['variantId'] != parent_mnv['variantId']]
        mnv_genes |= {gene_id for variant in nested_mnvs for gene_id in variant['transcripts'].keys()}
        parent_transcript = parent_mnv.get('main_transcript') or {}
        parent_details = [parent_transcript[key] for key in ['hgvsc', 'hgvsp'] if parent_transcript.get(key)]
        parent_name = _get_nested_variant_name(parent_mnv)
        discovery_notes = 'The following variants are part of the {variant_type} variant {parent}: {nested}'.format(
            variant_type='complex structural' if parent_mnv.get('svType') else 'multinucleotide',
            parent='{} ({})'.format(parent_name, ', '.join(parent_details)) if parent_details else parent_name,
            nested=', '.join(sorted([_get_nested_variant_name(v) for v in nested_mnvs])))
        for variant in nested_mnvs:
            variant['discovery_notes'] = discovery_notes
        saved_variants.remove(parent_mnv)
    return mnv_genes


def _process_comp_hets(family_id, potential_com_het_gene_variants, gene_ids, mnv_genes):
    compound_het_gene_id_by_family = {}
    for gene_id, comp_het_variants in potential_com_het_gene_variants.items():
        if gene_id in mnv_genes:
            continue
        if len(comp_het_variants) > 1:
            main_gene_ids = set()
            for variant in comp_het_variants:
                variant['inheritance_models'] = {'AR-comphet'}
                if variant['main_transcript']:
                    main_gene_ids.add(variant['main_transcript']['geneId'])
                else:
                    main_gene_ids.update(list(variant['transcripts'].keys()))
            if len(main_gene_ids) > 1:
                # This occurs in compound hets where some hits have a primary transcripts in different genes
                for gene_id in sorted(main_gene_ids):
                    if all(gene_id in variant['transcripts'] for variant in comp_het_variants):
                        compound_het_gene_id_by_family[family_id] = gene_id
                        gene_ids.add(gene_id)
    return compound_het_gene_id_by_family


def _parse_anvil_family_saved_variant(variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id):
    if variant['inheritance_models']:
        inheritance_mode = '|'.join([INHERITANCE_MODE_MAP[model] for model in variant['inheritance_models']])
    else:
        inheritance_mode = 'Unknown / Other'
    variant_genome_version = variant.get('genomeVersion') or genome_version
    parsed_variant = {
        'Gene_Class': 'Known',
        'inheritance_description': inheritance_mode,
        'variant_genome_build': GENOME_BUILD_MAP.get(variant_genome_version) or '',
        'discovery_notes': variant.get('discovery_notes', ''),
    }

    if 'discovery_tag_guids_by_name' in variant:
        discovery_tag_names = variant['discovery_tag_guids_by_name'].keys()
        is_novel = 'Y' if any('Novel gene' in name for name in discovery_tag_names) else 'N'
        parsed_variant['novel_mendelian_gene'] = is_novel
        _set_discovery_phenotype_class(parsed_variant, discovery_tag_names)
        if any('Tier 1' in name for name in discovery_tag_names):
            parsed_variant['Gene_Class'] = 'Tier 1 - Candidate'
        elif any('Tier 2' in name for name in discovery_tag_names):
            parsed_variant['Gene_Class'] = 'Tier 2 - Candidate'

    if variant.get('svType'):
        parsed_variant.update({
            'sv_name': _get_sv_name(variant),
            'sv_type': SV_TYPE_MAP.get(variant['svType'], variant['svType']),
        })
    else:
        gene_id = compound_het_gene_id_by_family.get(family_id) or variant['main_transcript']['geneId']
        parsed_variant.update({
            'Gene': genes_by_id[gene_id]['geneSymbol'],
            'Chrom': variant['chrom'],
            'Pos': str(variant['pos']),
            'Ref': variant['ref'],
            'Alt': variant['alt'],
            'hgvsc': (variant['main_transcript'].get('hgvsc') or '').split(':')[-1],
            'hgvsp': (variant['main_transcript'].get('hgvsp') or '').split(':')[-1],
            'Transcript': variant['main_transcript'].get('transcriptId'),
        })
    return variant['genotypes'], parsed_variant

def _get_subject_row(individual, has_dbgap_submission, airtable_metadata, parsed_variants, individual_id_map):
    features_present = [feature['id'] for feature in individual.features or []]
    features_absent = [feature['id'] for feature in individual.absent_features or []]
    onset = individual.onset_age

    solve_state = 'Unsolved'
    if parsed_variants:
        all_tier_2 = all(variant[1]['Gene_Class'] == 'Tier 2 - Candidate' for variant in parsed_variants)
        solve_state = 'Tier 2' if all_tier_2 else 'Tier 1'

    subject_row = {
        'entity:subject_id': individual.individual_id,
        'subject_id': individual.individual_id,
        'sex': Individual.SEX_LOOKUP[individual.sex],
        'ancestry': ANCESTRY_MAP.get(individual.population, ''),
        'ancestry_detail': ANCESTRY_DETAIL_MAP.get(individual.population, ''),
        'affected_status': Individual.AFFECTED_STATUS_LOOKUP[individual.affected],
        'congenital_status': Individual.ONSET_AGE_LOOKUP[onset] if onset else 'Unknown',
        'hpo_present': '|'.join(features_present),
        'hpo_absent': '|'.join(features_absent),
        'solve_state': solve_state,
        'proband_relationship': Individual.RELATIONSHIP_LOOKUP.get(individual.proband_relationship, ''),
        'paternal_id': individual_id_map.get(individual.father_id, ''),
        'maternal_id': individual_id_map.get(individual.mother_id, ''),
    }
    if airtable_metadata is not None:
        sequencing = airtable_metadata.get('SequencingProduct') or set()
        subject_row.update({
            'dbgap_submission': 'Yes' if has_dbgap_submission else 'No',
            'dbgap_study_id': airtable_metadata.get('dbgap_study_id', '') if has_dbgap_submission else '',
            'dbgap_subject_id': airtable_metadata.get('dbgap_subject_id', '') if has_dbgap_submission else '',
            'multiple_datasets': 'Yes' if len(sequencing) > 1 or (
            len(sequencing) == 1 and list(sequencing)[0] in MULTIPLE_DATASET_PRODUCTS) else 'No',
        })
    return subject_row


def _get_sample_row(sample, has_dbgap_submission, airtable_metadata):
    individual = sample.individual
    sample_row = {
        'entity:sample_id': individual.individual_id,
        'subject_id': individual.individual_id,
        'sample_id': sample.sample_id,
        'data_type': sample.sample_type,
        'date_data_generation': sample.loaded_date.strftime('%Y-%m-%d'),
        'sequencing_center': 'Broad',
    }
    if airtable_metadata is not None:
        sample_row['sample_provider'] = airtable_metadata.get('CollaboratorName') or ''
    if has_dbgap_submission:
        sample_row['dbgap_sample_id'] = airtable_metadata.get('dbgap_sample_id', '')
    return sample_row

def _get_discovery_rows(sample, parsed_variants, male_individual_guids):
    individual = sample.individual
    discovery_row = {
        'entity:discovery_id': individual.individual_id,
        'subject_id': individual.individual_id,
        'sample_id': sample.sample_id,
    }
    discovery_rows = []
    for genotypes, parsed_variant in parsed_variants:
        genotype = genotypes.get(individual.guid, {})
        is_x_linked = "X" in parsed_variant.get('Chrom', '')
        zygosity = _get_genotype_zygosity(
            genotype, is_hemi_variant=is_x_linked and individual.guid in male_individual_guids)
        if zygosity:
            variant_discovery_row = {
                'Zygosity': zygosity,
            }
            variant_discovery_row.update(parsed_variant)
            variant_discovery_row.update(discovery_row)
            discovery_rows.append(variant_discovery_row)
        else:
            discovery_rows.append(None)
    return discovery_rows


SINGLE_SAMPLE_FIELDS = ['Collaborator', 'dbgap_study_id', 'dbgap_subject_id', 'dbgap_sample_id']
LIST_SAMPLE_FIELDS = ['SequencingProduct', 'dbgap_submission']


def _get_airtable_samples_for_id_field(sample_ids, id_field, fields, session):
    raw_records = session.fetch_records(
        'Samples', fields=[id_field] + fields,
        or_filters={f'{{{id_field}}}': sample_ids},
    )

    records_by_id = defaultdict(list)
    for record in raw_records.values():
        records_by_id[record[id_field]].append(record)
    return records_by_id


def _get_airtable_samples(sample_ids, user, fields, list_fields=None):
    list_fields = list_fields or []
    all_fields = fields + list_fields

    session = AirtableSession(user)
    records_by_id = _get_airtable_samples_for_id_field(sample_ids, 'CollaboratorSampleID', all_fields, session)
    missing = set(sample_ids) - set(records_by_id.keys())
    if missing:
        records_by_id.update(_get_airtable_samples_for_id_field(missing, 'SeqrCollaboratorSampleID', all_fields, session))

    sample_records = {}
    for record_id, records in records_by_id.items():
        parsed_record = {}
        for field in fields:
            record_field = {
                record[field][0] if field == 'Collaborator' else record[field] for record in records if field in record
            }
            if len(record_field) > 1:
                error = 'Found multiple airtable records for sample {} with mismatched values in field {}'.format(
                    record_id, field)
                raise Exception(error)
            if record_field:
                parsed_record[field] = record_field.pop()
        for field in list_fields:
            parsed_record[field] = set()
            for record in records:
                if field in record:
                    parsed_record[field].update(record[field])

        sample_records[record_id] = parsed_record

    return sample_records, session


def _get_sample_airtable_metadata(sample_ids, user, include_collaborator=False):
    sample_records, session = _get_airtable_samples(
        sample_ids, user, fields=SINGLE_SAMPLE_FIELDS, list_fields=LIST_SAMPLE_FIELDS,
    )

    if include_collaborator:
        collaborator_ids = {record['Collaborator'] for record in sample_records.values() if 'Collaborator' in record}
        collaborator_map = session.fetch_records(
            'Collaborator', fields=['CollaboratorID'], or_filters={'RECORD_ID()': collaborator_ids}
        ) if collaborator_ids else {}

        for sample in sample_records.values():
            sample['CollaboratorName'] = collaborator_map.get(sample.get('Collaborator'), {}).get('CollaboratorID')

    return sample_records


# GREGoR metadata

SMID_FIELD = 'SMID'
PARTICIPANT_TABLE_COLUMNS = [
    'participant_id', 'internal_project_id', 'gregor_center', 'consent_code', 'recontactable', 'prior_testing',
    'pmid_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id', 'proband_relationship',
    'proband_relationship_detail', 'sex', 'sex_detail', 'reported_race', 'reported_ethnicity', 'ancestry_detail',
    'age_at_last_observation', 'affected_status', 'phenotype_description', 'age_at_enrollment',
]
GREGOR_FAMILY_TABLE_COLUMNS = [
    'family_id', 'consanguinity', 'consanguinity_detail', 'pedigree_file', 'pedigree_file_detail', 'family_history_detail',
]
PHENOTYPE_TABLE_COLUMNS = [
    'phenotype_id', 'participant_id', 'term_id', 'presence', 'ontology', 'additional_details', 'onset_age_range',
    'additional_modifiers',
]
ANALYTE_TABLE_COLUMNS = [
    'analyte_id', 'participant_id', 'analyte_type', 'analyte_processing_details', 'primary_biosample',
    'primary_biosample_id', 'primary_biosample_details', 'tissue_affected_status', 'age_at_collection',
    'participant_drugs_intake', 'participant_special_diet', 'hours_since_last_meal', 'passage_number', 'time_to_freeze',
    'sample_transformation_detail', 'quality_issues',
]
EXPERIMENT_TABLE_AIRTABLE_FIELDS = [
    'seq_library_prep_kit_method', 'read_length', 'experiment_type', 'targeted_regions_method',
    'targeted_region_bed_file', 'date_data_generation', 'target_insert_size', 'sequencing_platform',
]
EXPERIMENT_TABLE_COLUMNS = [
    'experiment_dna_short_read_id', 'analyte_id', 'experiment_sample_id',
] + EXPERIMENT_TABLE_AIRTABLE_FIELDS
READ_TABLE_AIRTABLE_FIELDS = [
    'aligned_dna_short_read_file', 'aligned_dna_short_read_index_file', 'md5sum', 'reference_assembly',
    'alignment_software', 'mean_coverage', 'analysis_details',
]
READ_TABLE_COLUMNS = ['aligned_dna_short_read_id', 'experiment_dna_short_read_id'] + READ_TABLE_AIRTABLE_FIELDS + ['quality_issues']
READ_TABLE_COLUMNS.insert(6, 'reference_assembly_details')
READ_TABLE_COLUMNS.insert(6, 'reference_assembly_uri')
READ_SET_TABLE_COLUMNS = ['aligned_dna_short_read_set_id', 'aligned_dna_short_read_id']
CALLED_TABLE_COLUMNS = [
    'called_variants_dna_short_read_id', 'aligned_dna_short_read_set_id', 'called_variants_dna_file', 'md5sum',
    'caller_software', 'variant_types', 'analysis_details',
]
ALL_AIRTABLE_COLUMNS = EXPERIMENT_TABLE_AIRTABLE_FIELDS + READ_TABLE_AIRTABLE_FIELDS + CALLED_TABLE_COLUMNS

TABLE_COLUMNS = {
    'participant': PARTICIPANT_TABLE_COLUMNS,
    'family': GREGOR_FAMILY_TABLE_COLUMNS,
    'phenotype': PHENOTYPE_TABLE_COLUMNS,
    'analyte': ANALYTE_TABLE_COLUMNS,
    'experiment_dna_short_read': EXPERIMENT_TABLE_COLUMNS,
    'aligned_dna_short_read': READ_TABLE_COLUMNS,
    'aligned_dna_short_read_set': READ_SET_TABLE_COLUMNS,
    'called_variants_dna_short_read': CALLED_TABLE_COLUMNS,
}
WARN_MISSING_TABLE_COLUMNS = {
    'participant': ['recontactable',  'reported_race', 'affected_status', 'phenotype_description', 'age_at_enrollment'],
}
WARN_MISSING_CONDITIONAL_COLUMNS = {
    'reported_race': lambda row: not row['ancestry_detail'],
    'age_at_enrollment': lambda row: row['affected_status'] == 'Affected'
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
    individuals = Individual.objects.filter(
        sample__in=get_search_samples(projects, active_only=False),
    ).distinct().prefetch_related('family__project', 'mother', 'father')

    airtable_sample_records, airtable_metadata_by_smid = _get_gregor_airtable_data(individuals, request.user)

    participant_rows = []
    family_map = {}
    phenotype_rows = []
    analyte_rows = []
    airtable_rows = []
    for individual in individuals:
        # family table
        family = individual.family
        if family not in family_map:
            family_map[family] = _get_gregor_family_row(family)

        if individual.consanguinity is not None and family_map[family]['consanguinity'] == 'Unknown':
            family_map[family]['consanguinity'] = 'Present' if individual.consanguinity else 'None suspected'

        # participant table
        airtable_sample = airtable_sample_records.get(individual.individual_id, {})
        participant_id = f'Broad_{individual.individual_id}'
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

        analyte_id = None
        # airtable data
        if airtable_sample:
            sm_id = airtable_sample[SMID_FIELD]
            analyte_id = f'Broad_{sm_id}'
            airtable_metadata = airtable_metadata_by_smid.get(sm_id)
            if airtable_metadata:
                experiment_ids = _get_experiment_ids(airtable_sample, airtable_metadata)
                airtable_rows.append(dict(analyte_id=analyte_id, **airtable_metadata, **experiment_ids))

        # analyte table
        analyte_rows.append(dict(participant_id=participant_id, analyte_id=analyte_id, **_get_analyte_row(individual)))

    files, warnings = _get_validated_gregor_files([
        ('participant', participant_rows),
        ('family', list(family_map.values())),
        ('phenotype', phenotype_rows),
        ('analyte', analyte_rows),
        ('experiment_dna_short_read', airtable_rows),
        ('aligned_dna_short_read', airtable_rows),
        ('aligned_dna_short_read_set', airtable_rows),
        ('called_variants_dna_short_read', airtable_rows),
    ])
    write_multiple_files_to_gs(files, file_path, request.user, file_format='tsv')

    return create_json_response({
        'info': [f'Successfully validated and uploaded Gregor Report for {len(family_map)} families'],
        'warnings': warnings,
    })


def _get_gregor_airtable_data(individuals, user):
    sample_records, session = _get_airtable_samples(
        individuals.order_by('individual_id').values_list('individual_id', flat=True), user,
        fields=[SMID_FIELD, 'CollaboratorSampleID', 'Recontactable'],
    )

    fields = ALL_AIRTABLE_COLUMNS
    airtable_metadata = session.fetch_records(
        'GREGoR Data Model',
        fields=[SMID_FIELD] + sorted(fields),
        or_filters={f'{SMID_FIELD}': {r[SMID_FIELD] for r in sample_records.values()}},
    )
    airtable_metadata_by_smid = {r[SMID_FIELD]: r for r in airtable_metadata.values()}

    return sample_records, airtable_metadata_by_smid


def _get_gregor_family_row(family):
    return {
        'family_id':  f'Broad_{family.family_id}',
        'internal_project_id': f'Broad_{family.project.name}',
        'consanguinity': 'Unknown',
        'pmid_id': '|'.join(family.pubmed_ids or []),
        'phenotype_description': family.coded_phenotype,
    }


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


def _get_analyte_row(individual):
    return {
        'analyte_type': individual.get_analyte_type_display(),
        'primary_biosample': individual.get_primary_biosample_display(),
        'tissue_affected_status': 'Yes' if individual.tissue_affected_status else 'No',
    }


def _get_experiment_ids(airtable_sample, airtable_metadata):
    collaborator_sample_id = airtable_sample['CollaboratorSampleID']
    experiment_dna_short_read_id = f'Broad_{airtable_metadata.get("experiment_type", "NA")}_{collaborator_sample_id}'
    return {
        'experiment_dna_short_read_id': experiment_dna_short_read_id,
        'experiment_sample_id': collaborator_sample_id,
        'aligned_dna_short_read_id': f'{experiment_dna_short_read_id}_1'
    }


def _get_validated_gregor_files(file_data):
    errors = []
    warnings = []
    try:
        validators, required_tables = _load_data_model_validators()
    except Exception as e:
        warnings.append(f'Unable to load data model for validation: {e}')
        validators = {}
        required_tables = set()

    missing_tables = required_tables.difference({f[0] for f in file_data})
    if missing_tables:
        warnings.append(
            f'The following tables are required in the data model but absent from the reports: {", ".join(missing_tables)}'
        )

    files = []
    for file_name, data in file_data:
        columns = TABLE_COLUMNS[file_name]
        files.append([file_name, columns, data])

        table_validator = validators.get(file_name)
        if not table_validator:
            warnings.append(f'No data model found for "{file_name}" table so no validation was performed')
            continue

        extra_columns = set(columns).difference(table_validator.keys())
        if extra_columns:
            col_summary = ', '.join(sorted(extra_columns))
            warnings.append(
                f'The following columns are included in the "{file_name}" table but are missing from the data model: {col_summary}'
            )
        missing_columns = set(table_validator.keys()).difference(columns)
        if missing_columns:
            col_summary = ', '.join(sorted(missing_columns))
            warnings.append(
                f'The following columns are included in the "{file_name}" data model but are missing in the report: {col_summary}'
            )

        for column in columns:
            _validate_column_data(
                column, file_name, data, column_validator=table_validator.get(column, {}),
                warnings=warnings, errors=errors,
            )

    if errors:
        raise ErrorsWarningsException(errors, warnings)

    return files, warnings


def _load_data_model_validators():
    response = requests.get(GREGOR_DATA_MODEL_URL)
    response.raise_for_status()
    table_models = response.json()['tables']
    validators = {
        t['table']: {c['column']: c for c in t['columns']}
        for t in table_models
    }
    required_tables = {t['table'] for t in table_models if t.get('required')}
    return validators, required_tables


def _validate_column_data(column, file_name, data, column_validator, warnings, errors):
    enum = column_validator.get('enumerations')
    required = column_validator.get('required')
    recommended = column in WARN_MISSING_TABLE_COLUMNS.get(file_name, [])
    if not (required or enum or recommended):
        return

    missing = []
    warn_missing = []
    invalid = []
    for row in data:
        value = row.get(column)
        if not value:
            if required:
                missing.append(_get_row_id(row))
            elif recommended:
                check_recommend_condition = WARN_MISSING_CONDITIONAL_COLUMNS.get(column)
                if not check_recommend_condition or check_recommend_condition(row):
                    warn_missing.append(_get_row_id(row))
        elif enum and value not in enum:
            invalid.append(f'{_get_row_id(row)} ({value})')
    if missing or warn_missing or invalid:
        airtable_summary = ' (from Airtable)' if column in ALL_AIRTABLE_COLUMNS else ''
        error_template = f'The following entries {{issue}} "{column}"{airtable_summary} in the "{file_name}" table'
        if missing:
            errors.append(
                f'{error_template.format(issue="are missing required")}: {", ".join(sorted(missing))}'
            )
        if invalid:
            invalid_values = f'Invalid values: {", ".join(sorted(invalid))}'
            errors.append(
                f'{error_template.format(issue="have invalid values for")}. Allowed values: {", ".join(enum)}. {invalid_values}'
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


def _get_parsed_saved_discovery_variants_by_family(families):
    return _get_saved_discovery_variants_by_family({'family__id__in': families}, parse_json=True)


def _get_project_saved_discovery_variants_by_family(project):
    return _get_saved_discovery_variants_by_family({'family__project': project}, parse_json=False)


def _get_saved_discovery_variants_by_family(variant_filter, parse_json=False):
    tag_types = VariantTagType.objects.filter(project__isnull=True, category='CMG Discovery Tags')

    project_saved_variants = SavedVariant.objects.filter(
        varianttag__variant_tag_type__in=tag_types,
        **variant_filter,
    ).order_by('created_date').distinct()

    if parse_json:
        project_saved_variants = get_json_for_saved_variants(
            project_saved_variants, add_details=True, additional_model_fields=['family_id'], additional_values={
                'discovery_tags': ArrayAgg(JSONObject(
                    name='varianttag__variant_tag_type__name',
                    guid='varianttag__guid',
                )),
            })
    else:
        project_saved_variants = project_saved_variants.prefetch_related(
            Prefetch('varianttag_set', to_attr='discovery_tags',
                 queryset=VariantTag.objects.filter(variant_tag_type__in=tag_types).select_related('variant_tag_type'),
            )).prefetch_related('variantfunctionaldata_set')

    saved_variants_by_family = defaultdict(list)
    for saved_variant in project_saved_variants:
        if parse_json:
            family_id = saved_variant.pop('familyId')
            saved_variant['discovery_tag_guids_by_name'] = {vt['name']: vt['guid'] for vt in
                                                             saved_variant.pop('discovery_tags')}
        else:
            family_id = saved_variant.family_id
        saved_variants_by_family[family_id].append(saved_variant)

    return saved_variants_by_family


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

    if family.post_discovery_omim_number:
        row["omim_number_post_discovery"] = family.post_discovery_omim_number

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


def _get_inheritance_models(variant_json, affected_individual_guids, unaffected_individual_guids, male_individual_guids):
    inheritance_models = set()

    affected_indivs_with_hom_alt_variants = set()
    affected_indivs_with_het_variants = set()
    unaffected_indivs_with_het_variants = set()
    is_x_linked = False

    genotypes = variant_json.get('genotypes')
    if genotypes:
        chrom = variant_json['chrom']
        is_x_linked = "X" in chrom
        for sample_guid, genotype in genotypes.items():
            zygosity = _get_genotype_zygosity(genotype, is_hemi_variant=is_x_linked and sample_guid in male_individual_guids)
            if zygosity in (HOM_ALT, HEMI) and sample_guid in unaffected_individual_guids:
                # No valid inheritance modes for hom alt unaffected individuals
                return set(), set()

            if zygosity in (HOM_ALT, HEMI) and sample_guid in affected_individual_guids:
                affected_indivs_with_hom_alt_variants.add(sample_guid)
            elif zygosity == HET and sample_guid in affected_individual_guids:
                affected_indivs_with_het_variants.add(sample_guid)
            elif zygosity == HET and sample_guid in unaffected_individual_guids:
                unaffected_indivs_with_het_variants.add(sample_guid)

    # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
    if affected_indivs_with_hom_alt_variants:
        if is_x_linked:
            inheritance_models.add("X-linked")
        else:
            inheritance_models.add("AR-homozygote")

    if not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
        if unaffected_individual_guids:
            inheritance_models.add("de novo")
        else:
            inheritance_models.add("AD")

    potential_compound_het_gene_ids = set()
    if (len(unaffected_individual_guids) < 2 or unaffected_indivs_with_het_variants) \
            and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants \
            and 'transcripts' in variant_json:
        potential_compound_het_gene_ids.update(list(variant_json['transcripts'].keys()))

    return inheritance_models, potential_compound_het_gene_ids


def _update_variant_inheritance(variant, affected_individual_guids, unaffected_individual_guids, male_individual_guids, potential_compound_het_genes):
    inheritance_models, potential_compound_het_gene_ids = _get_inheritance_models(
        variant.saved_variant_json, affected_individual_guids, unaffected_individual_guids, male_individual_guids)
    variant.saved_variant_json['inheritance'] = inheritance_models

    for gene_id in potential_compound_het_gene_ids:
        potential_compound_het_genes[gene_id].add(variant)

    variant_json = variant.saved_variant_json
    variant_json['selectedMainTranscriptId'] = variant.selected_main_transcript_id
    main_transcript = _get_variant_main_transcript(variant_json)
    if main_transcript.get('geneId'):
        variant.saved_variant_json['mainTranscriptGeneId'] = main_transcript['geneId']


def _get_genotype_zygosity(genotype, is_hemi_variant):
    num_alt = genotype.get('numAlt')
    cn = genotype.get('cn')
    if num_alt == 2 or cn == 0 or (cn != None and cn > 3):
        return HOM_ALT
    if num_alt == 1 or cn == 1 or cn == 3:
        return HEMI if is_hemi_variant else HET
    return None


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
                gene_id = _get_sv_name(variant.saved_variant_json)
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


DISCOVERY_PHENOTYPE_CLASSES = {
    'NEW': ['Tier 1 - Known gene, new phenotype', 'Tier 2 - Known gene, new phenotype'],
    'EXPAN': ['Tier 1 - Phenotype expansion', 'Tier 1 - Novel mode of inheritance', 'Tier 2 - Phenotype expansion'],
    'UE': ['Tier 1 - Phenotype not delineated', 'Tier 2 - Phenotype not delineated'],
    'KNOWN': ['Known gene for phenotype'],
}


def _set_discovery_phenotype_class(row, variant_tag_names):
    for phenotype_class, class_tag_names in DISCOVERY_PHENOTYPE_CLASSES.items():
        if any(tag in variant_tag_names for tag in class_tag_names):
            row['phenotype_class'] = phenotype_class
            break


def _set_discovery_details(row, variant_tag_names, variants):
    _set_discovery_phenotype_class(row, variant_tag_names)

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
