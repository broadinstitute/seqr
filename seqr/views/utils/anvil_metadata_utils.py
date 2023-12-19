from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models import F, Q, Value, CharField
from django.db.models.functions import Replace, JSONObject
from django.contrib.postgres.aggregates import ArrayAgg
import json

from matchmaker.models import MatchmakerSubmission
from reference_data.models import Omim
from seqr.models import Family, Individual
from seqr.views.utils.airtable_utils import get_airtable_samples
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_search_samples
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.variant_utils import get_variant_main_transcript, get_saved_discovery_variants_by_family, get_sv_name

SHARED_DISCOVERY_TABLE_VARIANT_COLUMNS = [
    'Gene', 'Gene_Class', 'inheritance_description', 'Zygosity', 'Chrom', 'Pos', 'Ref',
    'Alt', 'hgvsc', 'hgvsp', 'Transcript', 'sv_name', 'sv_type', 'discovery_notes',
]

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


def get_family_metadata(projects, additional_fields=None, additional_values=None, format_fields=None, include_metadata=False):
    values = {
        **(METADATA_FAMILY_VALUES if include_metadata else {}),
        **(additional_values or {}),
    }
    family_data = Family.objects.filter(project__in=projects).distinct().values(
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


def parse_anvil_metadata(projects, user, add_row, max_loaded_date=None, omit_airtable=False, include_metadata=False,
                          get_additional_sample_fields=None, get_additional_variant_fields=None, no_variant_zygosity=False):
    if max_loaded_date:
        individual_samples = _get_loaded_before_date_project_individual_samples(projects, max_loaded_date)
    else:
        individual_samples = _get_all_project_individual_samples(projects)

    family_values = dict(
        pmid_id=Replace('pubmed_ids__0', Value('PMID:'), Value(''), output_field=CharField()),
        phenotype_description=Replace(
            Replace('coded_phenotype', Value(','), Value(';'), output_field=CharField()),
            Value('\t'), Value(' '),
        ),
        genome_version=F('project__genome_version'),
        phenotype_groups=ArrayAgg(
            'project__projectcategory__name', distinct=True,
            filter=Q(project__projectcategory__name__in=PHENOTYPE_PROJECT_CATEGORIES),
        ),
        analysisStatus=METADATA_FAMILY_VALUES['analysisStatus'],
    )
    format_fields = {
        'phenotype_group': lambda f: '|'.join(f.pop('phenotype_groups')),
        'solve_state': lambda f: get_family_solve_state(f['analysisStatus']),
    }
    if include_metadata:
        family_values['analysis_groups'] = ArrayAgg(
            'analysisgroup__name', distinct=True, filter=Q(analysisgroup__isnull=False))
        format_fields['analysis_groups'] = lambda f: '; '.join(f['analysis_groups'])

    family_data_by_id = get_family_metadata(
        projects, additional_fields=['post_discovery_omim_numbers'], additional_values=family_values,
        format_fields=format_fields, include_metadata=include_metadata)

    individuals_by_family_id = defaultdict(list)
    individual_ids_map = {}
    sample_ids = set()
    for individual, sample in individual_samples.items():
        individuals_by_family_id[individual.family_id].append(individual)
        individual_ids_map[individual.id] = (individual.individual_id, individual.guid)
        if sample:
            sample_ids.add(sample.sample_id)

    individual_data_by_family = {
        family_id: _parse_family_individual_affected_data(family_individuals)
        for family_id, family_individuals in individuals_by_family_id.items()
    }

    sample_airtable_metadata = None if omit_airtable else _get_sample_airtable_metadata(list(sample_ids), user)

    saved_variants_by_family = _get_parsed_saved_discovery_variants_by_family(list(family_data_by_id.keys()))
    compound_het_gene_id_by_family, gene_ids = _process_saved_variants(
        saved_variants_by_family, individual_data_by_family)
    genes_by_id = get_genes(gene_ids)

    mim_numbers = set()
    for family in family_data_by_id.values():
        mim_numbers.update(family['post_discovery_omim_numbers'])
    mim_decription_map = {
        o.phenotype_mim_number: o.phenotype_description
        for o in Omim.objects.filter(phenotype_mim_number__in=mim_numbers)
    }

    matchmaker_individuals = set(MatchmakerSubmission.objects.filter(
        individual__in=individual_samples).values_list('individual_id', flat=True)) if include_metadata else set()

    for family_id, family_subject_row in family_data_by_id.items():
        saved_variants = saved_variants_by_family[family_id]

        family_individuals = individuals_by_family_id[family_id]
        genome_version = family_subject_row.pop('genome_version')

        mim_numbers = family_subject_row.pop('post_discovery_omim_numbers')
        if mim_numbers:
            family_subject_row.update({
                'disease_id': ';'.join(['OMIM:{}'.format(mim_number) for mim_number in mim_numbers]),
                'disease_description': ';'.join([
                    mim_decription_map.get(mim_number, '') for mim_number in mim_numbers]).replace(',', ';'),
            })

        affected_individual_guids = individual_data_by_family[family_id][0] if family_id in individual_data_by_family else []

        family_consanguinity = any(individual.consanguinity is True for individual in family_individuals)

        parsed_variants = [
            _parse_anvil_family_saved_variant(
                variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id,
                get_additional_variant_fields, allow_missing_discovery_genes=include_metadata,
            )
            for variant in saved_variants]

        family_row = {
            'family_id': family_subject_row['family_id'],
            'consanguinity': 'Present' if family_consanguinity else 'None suspected',
            **family_subject_row,
        }
        if len(affected_individual_guids) > 1:
            family_row['family_history'] = 'Yes'
        add_row(family_row, family_id, FAMILY_ROW_TYPE)

        if no_variant_zygosity:
            add_row([v for _, v in parsed_variants], family_id, DISCOVERY_ROW_TYPE)

        for individual in family_individuals:
            sample = individual_samples[individual]

            airtable_metadata = None
            has_dbgap_submission = None
            if sample and sample_airtable_metadata is not None:
                airtable_metadata = sample_airtable_metadata.get(sample.sample_id, {})
                dbgap_submission = airtable_metadata.get('dbgap_submission') or set()
                has_dbgap_submission = sample.sample_type in dbgap_submission

            subject_row = _get_subject_row(
                individual, has_dbgap_submission, airtable_metadata, individual_ids_map)
            if individual.id in matchmaker_individuals:
                subject_row['MME'] = 'Yes'
            subject_row.update(family_subject_row)
            add_row(subject_row, family_id, SUBJECT_ROW_TYPE)

            if sample:
                subject_id = subject_row['subject_id']
                sample_row = _get_sample_row(sample, subject_id, has_dbgap_submission, airtable_metadata, include_metadata, get_additional_sample_fields)
                add_row(sample_row, family_id, SAMPLE_ROW_TYPE)

            if not no_variant_zygosity:
                discovery_row = _get_discovery_rows(individual, sample, parsed_variants)
                add_row(discovery_row, family_id, DISCOVERY_ROW_TYPE)


def get_family_solve_state(analysis_status):
    return SOLVE_STATUS_LOOKUP.get(analysis_status, 'No')


def _parse_family_individual_affected_data(family_individuals):
    indiv_id_map = {individual.id: individual.guid for individual in family_individuals}
    return (
        {individual.guid for individual in family_individuals if individual.affected == Individual.AFFECTED_STATUS_AFFECTED},
        {individual.guid for individual in family_individuals if individual.affected == Individual.AFFECTED_STATUS_UNAFFECTED},
        {individual.guid for individual in family_individuals if individual.sex == Individual.SEX_MALE},
        {individual.guid: [
            indiv_id_map[parent_id] for parent_id in [individual.mother_id, individual.father_id]
            if parent_id in indiv_id_map
        ] for individual in family_individuals},
    )


def _get_nested_variant_name(variant, get_variant_id):
    return get_sv_name(variant) or get_variant_id(variant)


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


def _process_saved_variants(saved_variants_by_family, individual_data_by_family):
    gene_ids = set()
    compound_het_gene_id_by_family = {}
    for family_id, saved_variants in saved_variants_by_family.items():
        potential_com_het_gene_variants = defaultdict(list)
        potential_mnvs = defaultdict(list)
        for variant in saved_variants:
            variant['main_transcript'] = get_variant_main_transcript(variant)
            if variant['main_transcript']:
                gene_ids.add(variant['main_transcript']['geneId'])

            if family_id in individual_data_by_family:
                _update_variant_inheritance(variant, individual_data_by_family[family_id], potential_com_het_gene_variants)
            for guid in variant['discovery_tag_guids_by_name'].values():
                potential_mnvs[guid].append(variant)

        mnv_genes = _process_mnvs(potential_mnvs, saved_variants)
        compound_het_gene_id_by_family.update(
            _process_comp_hets(family_id, potential_com_het_gene_variants, gene_ids, mnv_genes)
        )

    return compound_het_gene_id_by_family, gene_ids


def _update_variant_inheritance(
        variant_json: dict, family_individual_data: tuple[set[str], set[str], set[str], dict[str: list[str]]],
        potential_com_het_gene_variants: dict[str: list[str]]) -> None:
    """Compute the inheritance mode for the given variant and family"""

    affected_individual_guids, unaffected_individual_guids, male_individual_guids, parent_guid_map = family_individual_data
    is_x_linked = 'X' in variant_json.get('chrom', '')

    genotype_zygosity = {
        sample_guid: get_genotype_zygosity(genotype, is_hemi_variant=is_x_linked and sample_guid in male_individual_guids)
        for sample_guid, genotype in variant_json.get('genotypes', {}).items()
    }
    inheritance_model, possible_comp_het = _get_inheritance_model(
        genotype_zygosity, affected_individual_guids, unaffected_individual_guids, parent_guid_map, is_x_linked)

    if possible_comp_het:
        for gene_id in variant_json.get('transcripts', {}).keys():
            potential_com_het_gene_variants[gene_id].append(variant_json)

    variant_json.update({
        'inheritance': inheritance_model,
        'genotype_zygosity': genotype_zygosity,
    })


HET = 'Heterozygous'
HOM_ALT = 'Homozygous'
HEMI = 'Hemizygous'

X_LINKED = 'X - linked'
RECESSIVE = 'Autosomal recessive (homozygous)'
DE_NOVO = 'de novo'
DOMINANT = 'Autosomal dominant'


def _get_inheritance_model(
        genotype_zygosity: dict[str, str], affected_individual_guids: set[str], unaffected_individual_guids: set[str],
        parent_guid_map: dict[str: list[str]], is_x_linked: bool) -> tuple[str, bool]:

    affected_zygosities = {genotype_zygosity[g] for g in affected_individual_guids if g in genotype_zygosity}
    unaffected_zygosities = {genotype_zygosity[g] for g in unaffected_individual_guids if g in genotype_zygosity}

    inheritance_model = ''
    possible_comp_het = False
    if any(zygosity in unaffected_zygosities for zygosity in {HOM_ALT, HEMI}):
        # No valid inheritance modes for hom alt unaffected individuals
        inheritance_model = ''
    elif any(zygosity in affected_zygosities for zygosity in {HOM_ALT, HEMI}):
        inheritance_model = X_LINKED if is_x_linked else RECESSIVE
    elif HET in affected_zygosities:
        if HET not in unaffected_zygosities:
            inherited = (not unaffected_individual_guids) or any(
                guid for guid in affected_individual_guids
                if genotype_zygosity.get(guid) == HET and
                any(genotype_zygosity.get(parent_guid) == HET for parent_guid in parent_guid_map[guid])
            )
            inheritance_model = DOMINANT if inherited else DE_NOVO

        if len(unaffected_individual_guids) < 2 or HET in unaffected_zygosities:
            possible_comp_het = True

    return inheritance_model, possible_comp_het


def get_genotype_zygosity(genotype, is_hemi_variant=False):
    num_alt = genotype.get('numAlt')
    cn = genotype.get('cn')
    if num_alt == 2 or cn == 0 or (cn != None and cn > 3):
        return HOM_ALT
    if num_alt == 1 or cn == 1 or cn == 3:
        return HEMI if is_hemi_variant else HET
    return None


def _process_mnvs(potential_mnvs, saved_variants):
    mnv_genes = set()
    for mnvs in potential_mnvs.values():
        if len(mnvs) <= 2:
            continue
        parent_mnv = next((v for v in mnvs if not v.get('populations')), mnvs[0])
        mnv_genes |= {gene_id for variant in mnvs for gene_id in variant['transcripts'].keys()}
        parent_transcript = parent_mnv.get('main_transcript') or {}
        discovery_notes = get_discovery_notes(
            {**parent_transcript, **parent_mnv}, mnvs, get_variant_id=lambda v: v['variantId'])
        for variant in mnvs:
            variant['discovery_notes'] = discovery_notes
        saved_variants.remove(parent_mnv)
    return mnv_genes


def get_discovery_notes(parent_mnv, mnvs, get_variant_id):
    variant_type = 'complex structural' if parent_mnv.get('svType') else 'multinucleotide'
    parent_name = _get_nested_variant_name(parent_mnv, get_variant_id)
    parent_details = [parent_mnv[key] for key in ['hgvsc', 'hgvsp'] if parent_mnv.get(key)]
    parent = f'{parent_name} ({", ".join(parent_details)})' if parent_details else parent_name
    mnv_names = [_get_nested_variant_name(v, get_variant_id) for v in mnvs]
    nested_mnvs = sorted([v for v in mnv_names if v != parent_name])
    return f'The following variants are part of the {variant_type} variant {parent}: {", ".join(nested_mnvs)}'


def _process_comp_hets(family_id, potential_com_het_gene_variants, gene_ids, mnv_genes):
    compound_het_gene_id_by_family = {}
    for gene_id, comp_het_variants in potential_com_het_gene_variants.items():
        if gene_id in mnv_genes:
            continue
        if len(comp_het_variants) > 1:
            main_gene_ids = set()
            for variant in comp_het_variants:
                variant['inheritance'] = 'Autosomal recessive (compound heterozygous)'
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


def _parse_anvil_family_saved_variant(variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id,
                                      get_additional_variant_fields, allow_missing_discovery_genes):
    parsed_variant = {
        'Gene_Class': 'Known',
        'inheritance_description': variant.get('inheritance') or 'Unknown / Other',
        'discovery_notes': variant.get('discovery_notes', ''),
        'Chrom': variant.get('chrom', ''),
        'Pos': str(variant.get('pos', '')),
    }
    if get_additional_variant_fields:
        parsed_variant.update(get_additional_variant_fields(variant, genome_version))

    if 'discovery_tag_guids_by_name' in variant:
        discovery_tag_names = variant['discovery_tag_guids_by_name'].keys()
        if any('Tier 1' in name for name in discovery_tag_names):
            parsed_variant['Gene_Class'] = 'Tier 1 - Candidate'
        elif any('Tier 2' in name for name in discovery_tag_names):
            parsed_variant['Gene_Class'] = 'Tier 2 - Candidate'

    if variant.get('svType'):
        parsed_variant.update({
            'sv_name': get_sv_name(variant),
            'sv_type': SV_TYPE_MAP.get(variant['svType'], variant['svType']),
        })
    else:
        gene_id = compound_het_gene_id_by_family.get(family_id) or variant['main_transcript'].get('geneId')
        if gene_id:
            gene = genes_by_id[gene_id]['geneSymbol']
        elif allow_missing_discovery_genes:
            gene = None
        else:
            family = Family.objects.get(id=family_id).family_id
            raise ErrorsWarningsException([f'Discovery variant {variant["variantId"]} in family {family} has no associated gene'])
        parsed_variant.update({
            'Gene': gene,
            'gene_id': gene_id,
            'Ref': variant['ref'],
            'Alt': variant['alt'],
            'hgvsc': (variant['main_transcript'].get('hgvsc') or '').split(':')[-1],
            'hgvsp': (variant['main_transcript'].get('hgvsp') or '').split(':')[-1],
            'Transcript': variant['main_transcript'].get('transcriptId'),
        })
    return variant.get('genotype_zygosity'), parsed_variant

def _get_subject_row(individual, has_dbgap_submission, airtable_metadata, individual_ids_map):
    features_present = [feature['id'] for feature in individual.features or []]
    features_absent = [feature['id'] for feature in individual.absent_features or []]
    onset = individual.onset_age

    paternal_ids = individual_ids_map.get(individual.father_id, ('', ''))
    maternal_ids = individual_ids_map.get(individual.mother_id, ('', ''))
    subject_row = {
        'subject_id': individual.individual_id,
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
        'paternal_id': paternal_ids[0],
        'paternal_guid': paternal_ids[1],
        'maternal_id': maternal_ids[0],
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


def _get_discovery_rows(individual, sample, parsed_variants):
    discovery_row = {
        'subject_id': individual.individual_id,
        'sample_id': sample.sample_id if sample else None,
    }
    discovery_rows = []
    for genotypes_zygosity, parsed_variant in parsed_variants:
        zygosity = genotypes_zygosity.get(individual.guid)
        if zygosity:
            variant_discovery_row = {
                'Zygosity': zygosity,
            }
            variant_discovery_row.update(parsed_variant)
            variant_discovery_row.update(discovery_row)
            discovery_rows.append(variant_discovery_row)
    return discovery_rows


SINGLE_SAMPLE_FIELDS = ['Collaborator', 'dbgap_study_id', 'dbgap_subject_id', 'dbgap_sample_id']
LIST_SAMPLE_FIELDS = ['SequencingProduct', 'dbgap_submission']


def _get_sample_airtable_metadata(sample_ids, user):
    sample_records, _ = get_airtable_samples(
        sample_ids, user, fields=SINGLE_SAMPLE_FIELDS, list_fields=LIST_SAMPLE_FIELDS,
    )
    return sample_records


def _format_variants(project_saved_variants, *args):
    variants = get_json_for_saved_variants(
        project_saved_variants, add_details=True, additional_model_fields=['family_id'], additional_values={
            'discovery_tags': ArrayAgg(JSONObject(
                name='varianttag__variant_tag_type__name',
                guid='varianttag__guid',
            )),
        })
    for saved_variant in variants:
        saved_variant['discovery_tag_guids_by_name'] = {vt['name']: vt['guid'] for vt in saved_variant.pop('discovery_tags')}
    return variants


def _get_parsed_saved_discovery_variants_by_family(families):
    return get_saved_discovery_variants_by_family(
        {'family__id__in': families}, _format_variants, lambda saved_variant: saved_variant.pop('familyId'),
    )
