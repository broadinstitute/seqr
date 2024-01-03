from collections import defaultdict
from datetime import datetime
from django.db.models import F, Q, Value, CharField, Case, When
from django.db.models.functions import Replace
from django.contrib.postgres.aggregates import ArrayAgg
import json
import requests
from typing import Callable, Iterable

from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology, Omim, GENOME_VERSION_LOOKUP
from seqr.models import Family, Individual, Sample, SavedVariant
from seqr.views.utils.airtable_utils import get_airtable_samples
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_search_samples
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.variant_utils import get_saved_discovery_variants_by_family

MONDO_BASE_URL = 'https://monarchinitiative.org/v3/api/entity'

HISPANIC = 'AMR'
MIDDLE_EASTERN = 'MDE'
OTHER_POPULATION = 'OTH'
ANCESTRY_MAP = {
  'AFR': 'Black or African American',
  HISPANIC: 'Hispanic or Latino',
  'ASJ': 'White',
  'EAS': 'Asian',
  'FIN': 'White',
  MIDDLE_EASTERN: 'Middle Eastern or North African',
  'NFE': 'White',
  'SAS': 'Asian',
}
ANCESTRY_DETAIL_MAP = {
  'ASJ': 'Ashkenazi Jewish',
  'EAS': 'East Asian',
  'FIN': 'Finnish',
  OTHER_POPULATION: 'Other',
  'SAS': 'South Asian',
}

MULTIPLE_DATASET_PRODUCTS = {
    'G4L WES + Array v1',
    'G4L WES + Array v2',
    'Standard Exome Plus GWAS Supplement Array',
    'Standard Germline Exome v5 Plus GSA Array',
    'Standard Germline Exome v5 Plus GWAS Supplement Array',
    'Standard Germline Exome v6 Plus GSA Array',
}

SOLVE_STATUS_LOOKUP = {
    **{s: 'Yes' for s in Family.SOLVED_ANALYSIS_STATUSES},
    **{s: 'Likely' for s in Family.STRONG_CANDIDATE_ANALYSIS_STATUSES},
    Family.ANALYSIS_STATUS_PARTIAL_SOLVE: 'Partial',
}

FAMILY_ROW_TYPE = 'family'
SUBJECT_ROW_TYPE = 'subject'
SAMPLE_ROW_TYPE = 'sample'
DISCOVERY_ROW_TYPE = 'discovery'

METADATA_FAMILY_VALUES = {
    'familyGuid': F('guid'),
    'projectGuid': F('project__guid'),
    'analysisStatus': F('analysis_status'),
    'displayName': F('family_id'),
}

METHOD_MAP = {
    Sample.SAMPLE_TYPE_WES: 'SR-ES',
    Sample.SAMPLE_TYPE_WGS: 'SR-GS',
}


def get_family_metadata(projects, additional_fields=None, additional_values=None, format_fields=None, include_metadata=False, family_filter=None):
    values = {
        **(METADATA_FAMILY_VALUES if include_metadata else {}),
        **(additional_values or {}),
    }
    families = Family.objects.filter(project__in=projects)
    if family_filter:
        families = families.filter(**family_filter)
    family_data = families.distinct().values(
        'id', 'family_id', 'project__name', *(additional_fields or []), **values,
    )

    family_data_by_id = {}
    for f in family_data:
        family_id = f.pop('id')
        f.update({
            'project_id': f.pop('project__name'),
            **{k: format(f) for k, format in (format_fields or {}).items()},
        })
        family_data_by_id[family_id] = f

    return family_data_by_id


def parse_anvil_metadata(projects, user, add_row, max_loaded_date=None, omit_airtable=False, include_metadata=False, family_fields=None,
                          get_additional_sample_fields=None, get_additional_individual_fields=None, include_discovery_sample_id=False,
                         include_mondo=False, individual_samples=None, individual_data_types=None, include_no_individual_families=False,
                         format_id=lambda s: s, airtable_fields=None, variant_filter=None, post_process_variant=None, proband_only_variants=False):
    individual_samples = individual_samples or (_get_loaded_before_date_project_individual_samples(projects, max_loaded_date) \
        if max_loaded_date else _get_all_project_individual_samples(projects))

    family_values = {
        'pmid_id': Replace('pubmed_ids__0', Value('PMID:'), Value(''), output_field=CharField()),
        'phenotype_description': Replace(
            Replace('coded_phenotype', Value(','), Value(';'), output_field=CharField()),
            Value('\t'), Value(' '),
        ),
        'analysisStatus': METADATA_FAMILY_VALUES['analysisStatus'],
    }
    format_fields = {
        'solve_state': lambda f: get_family_solve_state(f['analysisStatus']),
    }
    if include_metadata:
        family_values['analysis_groups'] = ArrayAgg(
            'analysisgroup__name', distinct=True, filter=Q(analysisgroup__isnull=False))
        format_fields['analysis_groups'] = lambda f: '; '.join(f['analysis_groups'])
    if family_fields:
        family_values.update({k: v['value'] for k, v in family_fields.items()})
        format_fields.update({k: v['format'] for k, v in family_fields.items()})
    if format_id:
        format_fields['family_id'] = lambda f: format_id(f['family_id'])

    additional_fields = ['post_discovery_omim_numbers']
    if include_mondo:
        additional_fields.append('mondo_id')

    family_data_by_id = get_family_metadata(
        projects, additional_fields=additional_fields, additional_values=family_values,
        format_fields=format_fields, include_metadata=include_metadata,
        family_filter=None if include_no_individual_families else {'individual__in': individual_samples})

    individuals_by_family_id = defaultdict(list)
    individual_ids_map = {}
    sample_ids = set()
    for individual, sample in individual_samples.items():
        individuals_by_family_id[individual.family_id].append(individual)
        individual_ids_map[individual.id] = (individual.individual_id, individual.guid)
        if sample:
            sample_ids.add(sample.sample_id)

    saved_variants_by_family = _get_parsed_saved_discovery_variants_by_family(list(family_data_by_id.keys()), variant_filter=variant_filter)

    mim_numbers = set()
    mondo_ids = set()
    for family in family_data_by_id.values():
        mim_numbers.update(family['post_discovery_omim_numbers'])
        if family.get('mondo_id'):
            family['mondo_id'] = f"MONDO:{family['mondo_id'].replace('MONDO:', '')}"
            mondo_ids.add(family['mondo_id'])
    mim_map = {
        o['phenotype_mim_number']: o for o in Omim.objects.filter(phenotype_mim_number__in=mim_numbers).values(
            'phenotype_mim_number', 'phenotype_description', 'phenotype_inheritance',
        )
    }
    mondo_map = {mondo_id: _get_mondo_condition_data(mondo_id) for mondo_id in mondo_ids}

    matchmaker_individuals = set(MatchmakerSubmission.objects.filter(
        individual__in=individual_samples).values_list('individual_id', flat=True)) if include_metadata else set()

    sample_airtable_metadata = None if omit_airtable else _get_sample_airtable_metadata(
        list(sample_ids) or [i[0] for i in individual_ids_map.values()], user, airtable_fields)

    for family_id, family_subject_row in family_data_by_id.items():
        saved_variants = saved_variants_by_family[family_id]

        family_individuals = individuals_by_family_id[family_id]

        mim_numbers = family_subject_row.pop('post_discovery_omim_numbers')
        if mim_numbers:
            mim_conditions = [mim_map.get(mim_number, {}) for mim_number in mim_numbers]
            family_subject_row.update({
                'disease_id': ';'.join(['OMIM:{}'.format(mim_number) for mim_number in mim_numbers]),
                'disease_description': ';'.join([o.get('phenotype_description', '') for o in mim_conditions]),
                'disease_inheritance': ';'.join([o.get('phenotype_inheritance', '') for o in mim_conditions]),
            })
        elif family_subject_row.get('mondo_id'):
            family_subject_row.update({
                'disease_id': family_subject_row['mondo_id'],
                **mondo_map[family_subject_row['mondo_id']],
            })

        affected_individuals = [individual for individual in family_individuals if individual.affected == Individual.AFFECTED_STATUS_AFFECTED]

        family_row = {
            'family_id': family_subject_row['family_id'],
            'consanguinity': next((
                'Present' if individual.consanguinity else 'None suspected'
                for individual in family_individuals if individual.consanguinity is not None
            ), 'Unknown'),
            **family_subject_row,
        }
        if len(affected_individuals) > 1:
            family_row['family_history'] = 'Yes'
        add_row(family_row, family_id, FAMILY_ROW_TYPE)

        for individual in family_individuals:
            sample = individual_samples[individual]

            airtable_metadata = None
            has_dbgap_submission = None
            if sample_airtable_metadata is not None:
                if sample:
                    airtable_metadata = sample_airtable_metadata.get(sample.sample_id, {})
                    dbgap_submission = airtable_metadata.get('dbgap_submission') or set()
                    has_dbgap_submission = sample.sample_type in dbgap_submission
                elif not sample_ids:
                    airtable_metadata = sample_airtable_metadata.get(individual.individual_id, {})

            subject_row = _get_subject_row(
                individual, has_dbgap_submission, airtable_metadata, individual_ids_map, get_additional_individual_fields,
                format_id,
            )
            if individual.id in matchmaker_individuals:
                subject_row['MME'] = 'Yes'
            subject_row.update(family_subject_row)
            add_row(subject_row, family_id, SUBJECT_ROW_TYPE)

            discovery_kwargs = {}
            subject_id = subject_row['subject_id']
            if sample:
                sample_row = _get_sample_row(sample, subject_id, has_dbgap_submission, airtable_metadata, include_metadata, get_additional_sample_fields)
                add_row(sample_row, family_id, SAMPLE_ROW_TYPE)
                if include_discovery_sample_id:
                    discovery_kwargs['sample_id'] = sample.sample_id

            if proband_only_variants and individual.proband_relationship != Individual.SELF_RELATIONSHIP:
                continue
            discovery_row = get_genetic_findings_rows(
                saved_variants, individual, participant_id=subject_row['subject_id'],
                individual_data_types=(individual_data_types or {}).get(subject_id),
                family_individuals=family_individuals if proband_only_variants else None, format_id=format_id,
                post_process_variant=post_process_variant or post_process_variant_metadata, **discovery_kwargs)
            add_row(discovery_row, family_id, DISCOVERY_ROW_TYPE)


def get_family_solve_state(analysis_status):
    return SOLVE_STATUS_LOOKUP.get(analysis_status, 'No')


def _get_nested_variant_name(v):
    return _get_sv_name(v) or f"{v['chrom']}-{v['pos']}-{v['ref']}-{v['alt']}"


def _get_sv_name(variant_json):
    if variant_json.get('svType'):
        return variant_json.get('svName') or '{svType}:chr{chrom}:{pos}-{end}'.format(**variant_json)
    return None


def _get_loaded_before_date_project_individual_samples(projects, max_loaded_date):
    max_loaded_date = datetime.strptime(max_loaded_date, '%Y-%m-%d')
    loaded_samples = _get_sorted_search_samples(projects).filter(
        loaded_date__lte=max_loaded_date).select_related('individual')
    #  Only return the oldest sample for each individual
    return {sample.individual: sample for sample in loaded_samples}


def _get_all_project_individual_samples(projects):
    samples_by_individual_id = {s.individual_id: s for s in _get_sorted_search_samples(projects)}
    individuals = Individual.objects.filter(family__project__in=projects)
    return {i: samples_by_individual_id.get(i.id) for i in individuals}


def _get_sorted_search_samples(projects):
    return get_search_samples(projects, active_only=False).order_by('-loaded_date')


HET = 'Heterozygous'
HOM_ALT = 'Homozygous'


def _get_genotype_zygosity(genotype):
    num_alt = genotype.get('numAlt')
    cn = genotype.get('cn')
    if num_alt == 2 or cn == 0 or (cn != None and cn > 3):
        return HOM_ALT
    if num_alt == 1 or cn == 1 or cn == 3:
        return HET
    return None


def post_process_variant_metadata(v, gene_variants, include_parent_mnvs=False):
    discovery_notes = None
    if len(gene_variants) > 2:
        parent_mnv = next((v for v in gene_variants if len(v['individual_genotype']) == 1), gene_variants[0])
        if parent_mnv['genetic_findings_id'] == v['genetic_findings_id'] and not include_parent_mnvs:
            return None
        variant_type = 'complex structural' if parent_mnv.get('svType') else 'multinucleotide'
        parent_name = _get_nested_variant_name(parent_mnv)
        parent_details = [parent_mnv[key] for key in ['hgvsc', 'hgvsp'] if parent_mnv.get(key)]
        parent = f'{parent_name} ({", ".join(parent_details)})' if parent_details else parent_name
        mnv_names = [_get_nested_variant_name(v) for v in gene_variants]
        nested_mnvs = sorted([v for v in mnv_names if v != parent_name])
        discovery_notes = f'The following variants are part of the {variant_type} variant {parent}: {", ".join(nested_mnvs)}'
    return {
        'sv_name': _get_sv_name(v),
        'notes': discovery_notes,
    }


def parse_variant_genetic_findings(variant_models: Iterable[SavedVariant], *args,
                                   variant_json_fields: list[str] = None, variant_model_annotations: dict = None):
    if variant_model_annotations:
        variant_models = variant_models.annotate(**variant_model_annotations)
    variant_json_fields = ['genotypes'] + (variant_json_fields or [])
    variants = []
    gene_ids = set()
    for variant in variant_models:
        chrom, pos = get_chrom_pos(variant.xpos)

        variant_json = variant.saved_variant_json
        variant_json['selectedMainTranscriptId'] = variant.selected_main_transcript_id
        main_transcript = _get_variant_main_transcript(variant)
        gene_id = main_transcript.get('geneId')
        gene_ids.add(gene_id)

        variants.append({
            'family_id': variant.family_id,
            'chrom': chrom,
            'pos': pos,
            'ref': variant.ref,
            'alt': variant.alt,
            'variant_reference_assembly': GENOME_VERSION_LOOKUP[variant_json['genomeVersion']],
            'gene_id': gene_id,
            'transcript': main_transcript.get('transcriptId'),
            'hgvsc': (main_transcript.get('hgvsc') or '').split(':')[-1],
            'hgvsp': (main_transcript.get('hgvsp') or '').split(':')[-1],
            'seqr_chosen_consequence': main_transcript.get('majorConsequence'),
            **{k: variant_json.get(k) for k in variant_json_fields},
            **{k: getattr(variant, k) for k in variant_model_annotations or {}},
        })

    genes_by_id = get_genes(gene_ids)
    for row in variants:
        row['gene'] = genes_by_id.get(row['gene_id'], {}).get('geneSymbol')
    return variants


def _get_variant_main_transcript(variant_model):
    variant = variant_model.saved_variant_json
    main_transcript_id = variant_model.selected_main_transcript_id or variant.get('mainTranscriptId')
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


def _get_subject_row(individual, has_dbgap_submission, airtable_metadata, individual_ids_map, get_additional_individual_fields, format_id):
    features_present = [feature['id'] for feature in individual.features or []]
    features_absent = [feature['id'] for feature in individual.absent_features or []]
    onset = individual.onset_age

    paternal_ids = individual_ids_map.get(individual.father_id, ('', ''))
    maternal_ids = individual_ids_map.get(individual.mother_id, ('', ''))
    subject_row = {
        'subject_id': format_id(individual.individual_id),
        'individual_guid': individual.guid,
        'sex': Individual.SEX_LOOKUP[individual.sex],
        'ancestry': ANCESTRY_MAP.get(individual.population, ''),
        'ancestry_detail': ANCESTRY_DETAIL_MAP.get(individual.population, ''),
        'affected_status': Individual.AFFECTED_STATUS_LOOKUP[individual.affected],
        'congenital_status': Individual.ONSET_AGE_LOOKUP[onset] if onset else 'Unknown',
        'hpo_present': '|'.join(features_present),
        'hpo_absent': '|'.join(features_absent),
        'disorders': individual.disorders,
        'filter_flags': json.dumps(individual.filter_flags) if individual.filter_flags else '',
        'proband_relationship': Individual.RELATIONSHIP_LOOKUP.get(individual.proband_relationship, ''),
        'paternal_id': format_id(paternal_ids[0]),
        'paternal_guid': paternal_ids[1],
        'maternal_id': format_id(maternal_ids[0]),
        'maternal_guid': maternal_ids[1],
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
    if get_additional_individual_fields:
        subject_row.update(get_additional_individual_fields(individual, airtable_metadata))
    return subject_row


def _get_sample_row(sample, subject_id, has_dbgap_submission, airtable_metadata, include_metadata, get_additional_sample_fields=None):
    sample_row = {
        'subject_id': subject_id,
        'sample_id': sample.sample_id,
    }
    if has_dbgap_submission:
        sample_row['dbgap_sample_id'] = airtable_metadata.get('dbgap_sample_id', '')
    if include_metadata:
        sample_row.update({
            'data_type': sample.sample_type,
            'date_data_generation': sample.loaded_date.strftime('%Y-%m-%d'),
        })
    if get_additional_sample_fields:
        sample_row.update(get_additional_sample_fields(sample, airtable_metadata))
    return sample_row


def get_genetic_findings_rows(rows: list[dict], individual: Individual, participant_id: str, format_id: Callable[[str], str] = '',
                              individual_data_types: Iterable[str] = None, family_individuals: dict[str, str] = None,
                              post_process_variant: Callable[[dict, list[dict]], dict] = None, **kwargs) -> list[dict]:
    parsed_rows = []
    variants_by_gene = defaultdict(list)
    for row in (rows or []):
        genotypes = row['genotypes']
        individual_genotype = genotypes.get(individual.guid) or {}
        zygosity = _get_genotype_zygosity(individual_genotype)
        if zygosity:
            heteroplasmy = individual_genotype.get('hl')
            findings_id = f'{participant_id}_{row["chrom"]}_{row["pos"]}'
            parsed_row = {
                'genetic_findings_id': findings_id,
                'participant_id': participant_id,
                'zygosity': zygosity if heteroplasmy is None else {
                    HET: 'Heteroplasmy',
                    HOM_ALT: 'Homoplasmy',
                }[zygosity],
                'allele_balance_or_heteroplasmy_percentage': heteroplasmy,
                'variant_inheritance': _get_variant_inheritance(individual, genotypes),
                **row,
                **kwargs,
            }
            if family_individuals is not None:
                parsed_row['additional_family_members_with_variant'] = '|'.join([
                    format_id(i.individual_id) for i in family_individuals
                    if i.guid != individual.guid and genotypes.get(i.guid) and _get_genotype_zygosity(genotypes[i.guid])
                ])
            if individual_data_types is not None:
                parsed_row['method_of_discovery'] = '|'.join([
                    METHOD_MAP.get(data_type) for data_type in individual_data_types if data_type != Sample.SAMPLE_TYPE_RNA
                ])
            parsed_rows.append(parsed_row)
            variants_by_gene[row['gene']].append({**parsed_row, 'individual_genotype': individual_genotype})

    to_remove = []
    for row in parsed_rows:
        del row['genotypes']
        if post_process_variant:
            update = post_process_variant(row, variants_by_gene[row['gene']])
            if update:
                row.update(update)
            else:
                to_remove.append(row)

    return [row for row in parsed_rows if row not in to_remove]


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


SINGLE_SAMPLE_FIELDS = ['Collaborator', 'dbgap_study_id', 'dbgap_subject_id', 'dbgap_sample_id']
LIST_SAMPLE_FIELDS = ['SequencingProduct', 'dbgap_submission']


def _get_sample_airtable_metadata(sample_ids, user, fields):
    sample_records, _ = get_airtable_samples(
        sample_ids, user, fields=fields or SINGLE_SAMPLE_FIELDS, list_fields=None if fields else LIST_SAMPLE_FIELDS,
    )
    return sample_records


def _get_parsed_saved_discovery_variants_by_family(families, variant_filter):
    return get_saved_discovery_variants_by_family(
        {'family__id__in': families, **(variant_filter or {})},
        format_variants=parse_variant_genetic_findings,
        get_family_id=lambda v: v.pop('family_id'),
        variant_json_fields=['svType', 'svName', 'end'],
        variant_model_annotations={
            'gene_known_for_phenotype': Case(When(
                Q(family__post_discovery_omim_numbers__len=0, family__mondo_id__isnull=True),
                then=Value('Candidate')), default=Value('Known')),
        },
    )


def _get_mondo_condition_data(mondo_id):
    try:
        response = requests.get(f'{MONDO_BASE_URL}/{mondo_id}', timeout=10)
        data = response.json()
        inheritance = data['inheritance']
        if inheritance:
            inheritance = HumanPhenotypeOntology.objects.get(hpo_id=inheritance['id']).name.replace(' inheritance', '')
        return {
            'disease_description': data['name'],
            'disease_inheritance': inheritance,
        }
    except Exception:
        return {}