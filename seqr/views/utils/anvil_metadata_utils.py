from collections import defaultdict
from datetime import datetime
from django.db.models import F, Q, Value, CharField, Aggregate
from django.db.models.functions import Replace
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import ArrayAgg
import requests
from typing import Callable, Iterable

from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology, Omim, GENOME_VERSION_LOOKUP
from seqr.models import Project, Family, Individual, Sample, SavedVariant, VariantTagType
from seqr.views.utils.airtable_utils import AirtableSession
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_search_samples
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.variant_utils import DISCOVERY_CATEGORY

MONDO_BASE_URL = 'https://monarchinitiative.org/v3/api/entity'

PARTICIPANT_TABLE = 'participant'
PHENOTYPE_TABLE = 'phenotype'
EXPERIMENT_TABLE = 'experiment_dna_short_read'
EXPERIMENT_LOOKUP_TABLE = 'experiment'
FINDINGS_TABLE = 'genetic_findings'

FINDING_METADATA_COLUMNS = [
    'gene_known_for_phenotype', 'known_condition_name', 'condition_id', 'condition_inheritance',
    'GREGoR_variant_classification', 'notes',
]
GENE_COLUMN = 'gene_of_interest'

HISPANIC = 'AMR'
OTHER = 'OTH'
ANCESTRY_MAP = {
  'AFR': 'Black or African American',
  'ASJ': 'White',
  'EAS': 'Asian',
  'FIN': 'White',
  'MDE': 'Middle Eastern or North African',
  'NFE': 'White',
  'SAS': 'Asian',
  'AmInd': 'American Indian or Alaska Native',
  'PaIsl': 'Native Hawaiian or Other Pacific Islander',
}
ANCESTRY_DETAIL_MAP = {
  'ASJ': 'Ashkenazi Jewish',
  'EAS': 'East Asian',
  'FIN': 'Finnish',
  OTHER: 'Other',
  HISPANIC: 'Other',
  'SAS': 'South Asian',
}
ETHNICITY_MAP = {
    HISPANIC: 'Hispanic or Latino',
}
ANCESTRY_LOOKUP = {v: k for k, v in ANCESTRY_MAP.items() if k not in ANCESTRY_DETAIL_MAP}
ANCESTRY_DETAIL_LOOKUP = {v: k for k, v in ANCESTRY_DETAIL_MAP.items() if v != 'Other'}
ETHNICITY_LOOKUP = {v: k for k, v in ETHNICITY_MAP.items()}

MULTIPLE_DATASET_PRODUCTS = {
    'G4L WES + Array v1',
    'G4L WES + Array v2',
    'Standard Exome Plus GWAS Supplement Array',
    'Standard Germline Exome v5 Plus GSA Array',
    'Standard Germline Exome v5 Plus GWAS Supplement Array',
    'Standard Germline Exome v6 Plus GSA Array',
}

ANALYSIS_SOLVE_STATUS_LOOKUP = {
    **{s: Individual.SOLVED for s in Family.SOLVED_ANALYSIS_STATUSES},
    Family.ANALYSIS_STATUS_PARTIAL_SOLVE: Individual.PARTIALLY_SOLVED,
    Family.ANALYSIS_STATUS_PROBABLE_SOLVE: Individual.PROBABLY_SOLVED,
}

MIM_INHERITANCE_MAP = {
    'Digenic dominant': 'Digenic',
    'Digenic recessive': 'Digenic',
    'X-linked dominant': 'X-linked',
    'X-linked recessive': 'X-linked',
}
MIM_INHERITANCE_MAP.update({inheritance: 'Other' for inheritance in [
    'Isolated cases', 'Multifactorial', 'Pseudoautosomal dominant', 'Pseudoautosomal recessive', 'Somatic mutation'
]})

FAMILY_ROW_TYPE = 'family'
SUBJECT_ROW_TYPE = 'subject'
SAMPLE_ROW_TYPE = 'sample'
DISCOVERY_ROW_TYPE = 'discovery'

FAMILY_NAME_DISPLAY_VALUES = {
    'familyGuid': F('guid'),
    'projectGuid': F('project__guid'),
    'displayName': F('family_id'),
}

METHOD_MAP = {
    Sample.SAMPLE_TYPE_WES: 'SR-ES',
    Sample.SAMPLE_TYPE_WGS: 'SR-GS',
}

FAMILY_INDIVIDUAL_FIELDS = ['family_id', 'internal_project_id', 'phenotype_description', 'pmid_id', 'solve_status']


def _format_hgvs(hgvs, *args):
    return (hgvs or '').split(':')[-1]


def _format_transcript_id(transcript_id, transcript):
    if transcript_id and (transcript.get('hgvsc') or '').startswith(transcript_id):
        return transcript['hgvsc'].split(':')[0]
    return transcript_id


TRANSCRIPT_FIELDS = {
    'transcript': {'seqr_field': 'transcriptId', 'format': _format_transcript_id},
    'hgvsc': {'format': _format_hgvs},
    'hgvsp': {'format': _format_hgvs},
}


def _get_family_metadata(family_filter, family_fields, include_family_name_display, include_family_sample_metadata, include_mondo, format_id):
    family_fields = {'analysis_groups': {
        'value': ArrayAgg('analysisgroup__name', distinct=True, filter=Q(analysisgroup__isnull=False)),
        'format': lambda f: '; '.join(f['analysis_groups']),
    }} if include_family_sample_metadata else family_fields
    include_family_name_display = include_family_name_display or include_family_sample_metadata
    family_data = Family.objects.filter(**family_filter).distinct().order_by('id').values(
        'id', 'family_id', 'post_discovery_omim_numbers',
        *(['post_discovery_mondo_id'] if include_mondo else []),
        internal_project_id=F('project__name'),
        pmid_id=Replace('pubmed_ids__0', Value('PMID:'), Value(''), output_field=CharField()),
        phenotype_description=Replace(
            Replace('coded_phenotype', Value(','), Value(';'), output_field=CharField()),
            Value('\t'), Value(' '),
        ),
        analysisStatus=F('analysis_status'),
        **(FAMILY_NAME_DISPLAY_VALUES if include_family_name_display else {}),
        **{k: v['value'] for k, v in (family_fields or {}).items()}
    )

    family_data_by_id = {}
    for f in family_data:
        family_id = f.pop('id')
        analysis_status = f['analysisStatus'] if include_family_name_display else f.pop('analysisStatus')
        solve_status = ANALYSIS_SOLVE_STATUS_LOOKUP.get(analysis_status, Individual.UNSOLVED)
        f.update({
            'solve_status': Individual.SOLVE_STATUS_LOOKUP[solve_status],
            **{k: v['format'](f) for k, v in (family_fields or {}).items()},
        })
        if format_id:
            f.update({k: format_id(f[k]) for k in ['family_id', 'internal_project_id']})
        family_data_by_id[family_id] = f

    return family_data_by_id


def parse_anvil_metadata(
        projects: Iterable[Project], user: User, add_row: Callable[[dict, str, str], None],
        max_loaded_date: str = None, family_fields: dict = None, format_id: Callable[[str], str] = lambda s: s,
        get_additional_sample_fields: Callable[[Sample, dict], dict] = None,
        get_additional_individual_fields: Callable[[Individual, dict], dict] = None,
        individual_samples: dict[Individual, Sample] = None, individual_data_types: dict[str, Iterable[str]] = None,
        airtable_fields: Iterable[str] = None, mme_value: Aggregate = None,
        variant_json_fields: Iterable[str] = None, variant_attr_fields: Iterable[str] = None, post_process_variant: Callable[[dict, list[dict]], dict] = None,
        include_no_individual_families: bool = False, omit_airtable: bool = False, include_family_name_display: bool = False, include_family_sample_metadata: bool = False,
        include_discovery_sample_id: bool = False, include_mondo: bool = False, omit_parent_mnvs: bool = False,
        proband_only_variants: bool = False):

    individual_samples = individual_samples or (_get_loaded_before_date_project_individual_samples(projects, max_loaded_date) \
        if max_loaded_date else _get_all_project_individual_samples(projects))

    family_data_by_id = _get_family_metadata(
        {'project__in': projects} if include_no_individual_families else {'individual__in': individual_samples},
        family_fields, include_family_name_display, include_family_sample_metadata, include_mondo, format_id
    )

    individuals_by_family_id = defaultdict(list)
    individual_ids_map = {}
    sample_ids = set()
    for individual, sample in individual_samples.items():
        individuals_by_family_id[individual.family_id].append(individual)
        individual_ids_map[individual.id] = (individual.individual_id, individual.guid)
        if sample:
            sample_ids.add(sample.sample_id)

    saved_variants_by_family = _get_parsed_saved_discovery_variants_by_family(
        list(family_data_by_id.keys()), bool(mme_value), variant_json_fields, variant_attr_fields,
    )

    condition_map = _get_condition_map(family_data_by_id.values())

    sample_airtable_metadata = None if omit_airtable else _get_sample_airtable_metadata(
        list(sample_ids) or [i[0] for i in individual_ids_map.values()], user, airtable_fields)

    matchmaker_individuals = {m['individual_id']: m['value'] for m in MatchmakerSubmission.objects.filter(
        individual__in=individual_samples).values('individual_id', value=mme_value)} if mme_value else {}

    for family_id, family_subject_row in family_data_by_id.items():
        saved_variants = saved_variants_by_family[family_id]

        family_individuals = individuals_by_family_id[family_id]

        _update_conditions(
            family_subject_row, saved_variants, *condition_map, set_conditions_for_variants=proband_only_variants,
        )

        subject_family_row = {k: family_subject_row.pop(k) for k in FAMILY_INDIVIDUAL_FIELDS}
        family_row = {
            'family_id': subject_family_row['family_id'],
            **family_subject_row,
        }
        if not include_family_name_display:
            family_row['consanguinity'] = next((
                'Present' if individual.consanguinity else 'None suspected'
                for individual in family_individuals if individual.consanguinity is not None
            ), 'Unknown')
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
                subject_row['MME'] = matchmaker_individuals[individual.id]
            subject_row.update(subject_family_row)
            if individual.solve_status:
                subject_row['solve_status'] = Individual.SOLVE_STATUS_LOOKUP[individual.solve_status]
            elif individual.affected != Individual.AFFECTED_STATUS_AFFECTED:
                subject_row['solve_status'] = 'Unaffected'
            add_row(subject_row, family_id, SUBJECT_ROW_TYPE)

            participant_id = subject_row['participant_id']
            if sample:
                sample_row = _get_sample_row(sample, participant_id, has_dbgap_submission, airtable_metadata, include_family_sample_metadata, get_additional_sample_fields)
                add_row(sample_row, family_id, SAMPLE_ROW_TYPE)

            if proband_only_variants and individual.proband_relationship != Individual.SELF_RELATIONSHIP:
                continue
            discovery_row = _get_genetic_findings_rows(
                saved_variants, individual, subject_family_row, participant_id=participant_id,
                format_id=format_id, omit_parent_mnvs=omit_parent_mnvs,
                individual_data_types=(individual_data_types or {}).get(participant_id),
                family_individuals=family_individuals if proband_only_variants else None,
                sample=sample if include_discovery_sample_id else None,
                post_process_variant=post_process_variant,
            )
            add_row(discovery_row, family_id, DISCOVERY_ROW_TYPE)


def _get_nested_variant_name(v):
    return v['sv_name'] or f"{v['chrom']}-{v['pos']}-{v['ref']}-{v['alt']}"


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
HEMI = 'Hemizygous'


def _get_genotype_zygosity(genotype, individual=None, variant=None):
    num_alt = genotype.get('numAlt')
    cn = genotype.get('cn')
    if num_alt == 2 or cn == 0 or (cn != None and cn > 3):
        return HEMI if (variant or {}).get('chrom') == 'X' and individual.sex in Individual.MALE_SEXES else HOM_ALT
    if num_alt == 1 or cn == 1 or cn == 3:
        return HET
    return None


def _get_discovery_notes(variant, gene_variants, omit_parent_mnvs):
    parent_mnv = next((v for v in gene_variants if len(v['individual_genotype']) == 1), gene_variants[0])
    is_parent_mnv = (parent_mnv['genetic_findings_id'], parent_mnv['alt']) == (variant['genetic_findings_id'], variant['alt'])
    should_skip = is_parent_mnv if omit_parent_mnvs else not is_parent_mnv
    if should_skip:
        return None
    variant_type = 'complex structural' if parent_mnv.get('sv_type') else 'multinucleotide'
    parent_name = _get_nested_variant_name(parent_mnv)
    parent_details = [parent_mnv[key] for key in ['hgvsc', 'hgvsp'] if parent_mnv.get(key)]
    parent = f'{parent_name} ({", ".join(parent_details)})' if parent_details else parent_name
    mnv_names = [_get_nested_variant_name(v) for v in gene_variants]
    nested_mnvs = sorted([v for v in mnv_names if v != parent_name])
    return f'The following variants are part of the {variant_type} variant {parent}: {", ".join(nested_mnvs)}'

VARIANT_TYPES = [
    ('SV', lambda ref, alt: not alt),
    ('SNV', lambda ref, alt: len(ref) == 1 and len(alt) == 1),
    ('RE', lambda ref, alt: all(['[' in allele and ']' in allele for allele in [ref, alt]])),
]

def _get_parsed_saved_discovery_variants_by_family(
        families: Iterable[Family], include_metadata: bool, variant_json_fields: list[str],
        variant_attr_fields: list[str],
):
    tag_types = VariantTagType.objects.filter(project__isnull=True, category=DISCOVERY_CATEGORY)

    annotations = dict(
        tags=ArrayAgg('varianttag__variant_tag_type__name', distinct=True),
        notes=ArrayAgg('variantnote__note', distinct=True, filter=Q(variantnote__report=True)),
        partial_hpo_terms=ArrayAgg('variantfunctionaldata__metadata', distinct=True, filter=Q(variantfunctionaldata__functional_data_tag='Partial Phenotype Contribution')),
        validated_name=ArrayAgg('variantfunctionaldata__metadata', distinct=True, filter=Q(variantfunctionaldata__functional_data_tag='Validated Name')),
    )

    project_saved_variants = SavedVariant.objects.filter(
        varianttag__variant_tag_type__in=tag_types, family__id__in=families,
    ).order_by('created_date').distinct().annotate(**annotations)

    variants = []
    gene_ids = set()
    for variant in project_saved_variants:
        chrom, pos = get_chrom_pos(variant.xpos)

        variant_json = variant.saved_variant_json
        main_transcript = _get_variant_main_transcript(variant)
        gene_id = main_transcript.get('geneId')
        gene_ids.add(gene_id)
        sv_type = variant_json.get('svType')
        variant_type = next(
            (variant_type for variant_type, has_type in VARIANT_TYPES if has_type(variant.ref, variant.alt)),
            'INDEL')

        partial_hpo_terms = variant.partial_hpo_terms[0] if variant.partial_hpo_terms else ''
        phenotype_contribution = 'Partial' if partial_hpo_terms else 'Full'
        if partial_hpo_terms == 'Uncertain':
            phenotype_contribution = 'Uncertain'
            partial_hpo_terms = ''

        parsed_variant = {
            'chrom': 'MT' if chrom == 'M' else chrom,
            'pos': pos,
            'variant_reference_assembly': GENOME_VERSION_LOOKUP[variant_json['genomeVersion']],
            'gene_id': gene_id,
            'gene_ids': [gene_id] if gene_id else variant_json.get('transcripts', {}).keys(),
            'gene_known_for_phenotype': 'Known' if 'Known gene for phenotype' in variant.tags else 'Candidate',
            'phenotype_contribution': phenotype_contribution,
            'partial_contribution_explained': partial_hpo_terms.replace(', ', '|'),
            'notes': variant.notes,
            'sv_type': sv_type,
            'sv_name': (variant_json.get('svName') or '{svType}:chr{chrom}:{pos}-{end}'.format(**variant_json)) if sv_type else None,
            'variant_type': variant_type,
            'validated_name': variant.validated_name[0] if variant.validated_name else None,
            **{k: _get_transcript_field(k, config, main_transcript) for k, config in TRANSCRIPT_FIELDS.items()},
            **{k: variant_json.get(k) for k in ['genotypes'] + (variant_json_fields or [])},
            **{k: variant_json.get(field) if sv_type else None for k, field in [('chrom_end', 'endChrom'), ('pos_end', 'end')]},
            'ClinGen_allele_ID': variant_json.get('CAID'),
            **{k: getattr(variant, k) for k in ['family_id', 'ref', 'alt'] + (variant_attr_fields or [])},
        }
        if include_metadata:
            parsed_variant.update({
                'seqr_chosen_consequence': main_transcript.get('majorConsequence'),
            })
        variants.append(parsed_variant)

    genes_by_id = get_genes(gene_ids)

    saved_variants_by_family = defaultdict(list)
    for row in variants:
        gene_id = row['gene_id'] if include_metadata else row.pop('gene_id')
        row[GENE_COLUMN] = genes_by_id.get(gene_id, {}).get('geneSymbol')
        family_id = row.pop('family_id')
        saved_variants_by_family[family_id].append(row)

    return saved_variants_by_family


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


def _get_transcript_field(field, config, transcript):
    value = transcript.get(config.get('seqr_field', field))
    if config.get('format'):
        value = config['format'](value, transcript)
    return value


def _get_subject_row(individual, has_dbgap_submission, airtable_metadata, individual_ids_map, get_additional_individual_fields, format_id):
    paternal_ids = individual_ids_map.get(individual.father_id, ('', ''))
    maternal_ids = individual_ids_map.get(individual.mother_id, ('', ''))
    sex = individual.sex
    sex_detail = None
    if sex in Individual.MALE_ANEUPLOIDIES:
        sex_detail = sex
        sex = Individual.SEX_MALE
    elif sex in Individual.FEMALE_ANEUPLOIDIES:
        sex_detail = sex
        sex = Individual.SEX_FEMALE
    subject_row = {
        'participant_id': format_id(individual.individual_id),
        'sex': Individual.SEX_LOOKUP[sex],
        'sex_detail': sex_detail,
        'reported_race': ANCESTRY_MAP.get(individual.population, ''),
        'ancestry_detail': ANCESTRY_DETAIL_MAP.get(individual.population, ''),
        'reported_ethnicity': ETHNICITY_MAP.get(individual.population, ''),
        'affected_status': Individual.AFFECTED_STATUS_LOOKUP[individual.affected],
        'features': individual.features,
        'absent_features': individual.absent_features,
        'proband_relationship': Individual.RELATIONSHIP_LOOKUP.get(individual.proband_relationship, ''),
        'paternal_id': format_id(paternal_ids[0]),
        'maternal_id': format_id(maternal_ids[0]),
    }
    if airtable_metadata is not None:
        subject_row.update({
            'dbgap_study_id': airtable_metadata.get('dbgap_study_id', '') if has_dbgap_submission else '',
            'dbgap_subject_id': airtable_metadata.get('dbgap_subject_id', '') if has_dbgap_submission else '',
        })
    if get_additional_individual_fields:
        subject_row.update(get_additional_individual_fields(individual, airtable_metadata, has_dbgap_submission, maternal_ids, paternal_ids))
    return subject_row


def anvil_export_airtable_fields(airtable_metadata, has_dbgap_submission):
    if airtable_metadata is None:
        return {}
    sequencing = airtable_metadata.get('SequencingProduct') or set()
    return {
        'dbgap_submission': 'Yes' if has_dbgap_submission else 'No',
        'multiple_datasets': 'Yes' if len(sequencing) > 1 or (
                len(sequencing) == 1 and list(sequencing)[0] in MULTIPLE_DATASET_PRODUCTS) else 'No',
    }


def _get_sample_row(sample, participant_id, has_dbgap_submission, airtable_metadata, include_family_sample_metadata, get_additional_sample_fields=None):
    sample_row = {
        'participant_id': participant_id,
        'sample_id': sample.sample_id,
    }
    if has_dbgap_submission:
        sample_row['dbgap_sample_id'] = airtable_metadata.get('dbgap_sample_id', '')
    if include_family_sample_metadata:
        sample_row.update({
            'data_type': sample.sample_type,
            'date_data_generation': sample.loaded_date.strftime('%Y-%m-%d'),
        })
    if get_additional_sample_fields:
        sample_row.update(get_additional_sample_fields(sample, airtable_metadata))
    return sample_row


def _get_genetic_findings_rows(rows: list[dict], individual: Individual, family_row: dict, participant_id: str,
                              individual_data_types: Iterable[str], family_individuals: dict[str, str],
                              post_process_variant: Callable[[dict, list[dict]], dict],
                              format_id: Callable[[str], str], omit_parent_mnvs: bool, sample: Sample) -> list[dict]:
    parsed_rows = []
    variants_by_gene = defaultdict(list)
    for row in (rows or []):
        genotypes = row['genotypes']
        individual_genotype = genotypes.get(individual.guid) or {}
        zygosity = _get_genotype_zygosity(individual_genotype, individual, row)
        copy_number = individual_genotype.get('cn') or -1
        if zygosity:
            heteroplasmy = individual_genotype.get('hl')
            findings_id = f'{participant_id}_{row["chrom"]}_{row["pos"]}'
            if row['sv_type']:
                findings_id += f'_{row["sv_type"]}'
            parsed_row = {
                'genetic_findings_id': findings_id,
                'participant_id': participant_id,
                'zygosity': zygosity if heteroplasmy is None else {
                    HET: 'Heteroplasmy',
                    HOM_ALT: 'Homoplasmy',
                }[zygosity],
                'copy_number': copy_number if copy_number >= 0 else None,
                'allele_balance_or_heteroplasmy_percentage': heteroplasmy,
                'variant_inheritance': _get_variant_inheritance(individual, genotypes),
                **row,
            }
            if family_individuals is not None:
                parsed_row['additional_family_members_with_variant'] = '|'.join([
                    format_id(i.individual_id) for i in family_individuals
                    if i.guid != individual.guid and genotypes.get(i.guid) and _get_genotype_zygosity(genotypes[i.guid])
                ])
            if individual_data_types is not None:
                parsed_row['method_of_discovery'] = '|'.join([
                    METHOD_MAP.get(data_type) for data_type in individual_data_types if data_type in Sample.SAMPLE_TYPE_LOOKUP
                ])
            if sample is not None:
                parsed_row['sample_id'] = sample.sample_id
            parsed_rows.append(parsed_row)
            variants_by_gene[row[GENE_COLUMN]].append({**parsed_row, 'individual_genotype': individual_genotype})

    to_remove = []
    for row in parsed_rows:
        del row['genotypes']

        gene_variants = variants_by_gene[row[GENE_COLUMN]]
        notes = row['notes'] or []
        if len(gene_variants) > 2:
            discovery_notes = _get_discovery_notes(row, gene_variants, omit_parent_mnvs)
            if discovery_notes is None:
                to_remove.append(row)
                continue
            else:
                notes.append(discovery_notes)
        if family_row['pmid_id']:
            notes.append(f'This individual is published in PMID{family_row["pmid_id"]}')
        row['notes'] = '. '.join(notes)

        if post_process_variant:
            row.update(post_process_variant(row, gene_variants))

    return [row for row in parsed_rows if row not in to_remove]


def _get_variant_inheritance(individual, genotypes):
    parental_inheritance = tuple(
        None if parent is None or parent.guid not in genotypes else genotypes[parent.guid].get('numAlt', -1) > 0
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


def _get_sample_airtable_metadata(sample_ids, user, airtable_fields):
    fields, list_fields = airtable_fields or [SINGLE_SAMPLE_FIELDS, LIST_SAMPLE_FIELDS]
    all_fields = fields + list_fields

    records_by_id = AirtableSession(user).get_samples_for_sample_ids(sample_ids, all_fields)

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
                raise ErrorsWarningsException([error])
            if record_field:
                parsed_record[field] = record_field.pop()
        for field in list_fields:
            parsed_record[field] = {} if airtable_fields else set()
            for record in records:
                if field in record:
                    if airtable_fields:
                        parsed_record[field][record['airtable_id']] = record[field]
                    else:
                        parsed_record[field].update(record[field])

        sample_records[record_id] = parsed_record

    return sample_records


def _get_condition_map(families):
    mim_numbers = set()
    mondo_ids = set()
    for family in families:
        mim_numbers.update(family['post_discovery_omim_numbers'])
        if family.get('post_discovery_mondo_id'):
            family['post_discovery_mondo_id'] = f"MONDO:{family['post_discovery_mondo_id'].replace('MONDO:', '')}"
            mondo_ids.add(family['post_discovery_mondo_id'])

    omim_conditions_by_id_gene = defaultdict(lambda: defaultdict(list))
    for omim in Omim.objects.filter(phenotype_mim_number__in=mim_numbers).values(
            'phenotype_mim_number', 'phenotype_description', 'phenotype_inheritance', 'chrom', 'start', 'end',
            'gene__gene_id', 'gene__gene_symbol',
    ):
        omim_conditions_by_id_gene[omim['phenotype_mim_number']][omim['gene__gene_id']].append(omim)

    mondo_condition_map = {mondo_id: _get_mondo_condition_data(mondo_id) for mondo_id in mondo_ids}

    return omim_conditions_by_id_gene, mondo_condition_map


def _get_mondo_condition_data(mondo_id):
    try:
        response = requests.get(f'{MONDO_BASE_URL}/{mondo_id}', timeout=10)
        data = response.json()
        inheritance = data['inheritance']
        if inheritance:
            inheritance = HumanPhenotypeOntology.objects.get(hpo_id=inheritance['id']).name.replace(' inheritance', '')
        return {
            'known_condition_name': data['name'],
            'condition_inheritance': inheritance or 'Unknown',
        }
    except Exception:
        return {}


def _update_conditions(family_subject_row, variants, omim_conditions, mondo_conditions, set_conditions_for_variants):
    mondo_id = family_subject_row.pop('post_discovery_mondo_id', None)
    mondo_condition = {'condition_id': mondo_id, **mondo_conditions[mondo_id]} if mondo_id else {}
    mim_numbers = family_subject_row.pop('post_discovery_omim_numbers') or []

    family_conditions = []
    for v in variants:
        variant_conditions = [
            c for mim_number in mim_numbers for c in omim_conditions[mim_number][None]
            if c['chrom'] == v['chrom'] and c['start'] <= v['pos'] <= c['end']
        ]
        gene_ids = v.pop('gene_ids')
        for mim_number in mim_numbers:
            for gene_id in gene_ids:
                variant_conditions += omim_conditions[mim_number][gene_id]

        if set_conditions_for_variants:
            if v['sv_type'] and mim_numbers:
                # For SVs report the gene linked to the condition instead of the annotated gene if conflicting
                if not variant_conditions:
                    possible_gene_conditions = [
                        conditions for mim_number in mim_numbers
                        for gene_id, conditions in omim_conditions[mim_number].items() if gene_id and conditions
                    ]
                    if len(possible_gene_conditions) == 1:
                        variant_conditions = possible_gene_conditions[0]
                condition_genes = {c['gene__gene_symbol'] for c in variant_conditions}
                if len(condition_genes) == 1:
                    v[GENE_COLUMN] = list(condition_genes)[0]
            conditions = _format_omim_conditions(variant_conditions) if variant_conditions else mondo_condition
            v.update(conditions)
        else:
            family_conditions += variant_conditions

    if set_conditions_for_variants:
        return

    # Preferentially include conditions associated with discovery genes/regions, but fall back to all
    if not family_conditions:
        family_conditions = [
            c for mim_number in mim_numbers for conditions in omim_conditions[mim_number].values() for c in conditions
        ] or [{'phenotype_mim_number': mim_number} for mim_number in mim_numbers]

    family_condition = _format_omim_conditions(family_conditions) if family_conditions else mondo_condition
    if family_condition:
        family_subject_row.update(family_condition)


def _format_omim_conditions(conditions):
    return {
        'condition_id': '|'.join(sorted({f"OMIM:{o['phenotype_mim_number']}" for o in conditions})),
        'known_condition_name': '|'.join(sorted({o['phenotype_description'] for o in conditions if o.get('phenotype_description')})),
        'condition_inheritance': '|'.join(sorted({
            MIM_INHERITANCE_MAP.get(i, i) for o in conditions if o.get('phenotype_inheritance') for i in o['phenotype_inheritance'].split(', ')
        })) or 'Unknown',
    }


def parse_population(row):
    if row['reported_ethnicity'] in ETHNICITY_LOOKUP:
        return ETHNICITY_LOOKUP[row['reported_ethnicity']]

    detail = row['ancestry_detail'].title()
    race = row['reported_race']
    if race == 'NA' or not (detail or race):
        return ''
    if race == 'Asian':
        # seqr subdivides asian so need to determine which subpopulation to assign
        is_south_asian = detail and ('south' in detail.lower() or 'india' in detail.lower())
        detail = 'South Asian' if is_south_asian else 'East Asian'

    if detail in ANCESTRY_DETAIL_LOOKUP:
        return ANCESTRY_DETAIL_LOOKUP[detail]

    if '|' in race:
        return OTHER

    return ANCESTRY_LOOKUP[race]
