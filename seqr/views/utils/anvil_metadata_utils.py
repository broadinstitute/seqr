from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models import F, Q, Value, CharField
from django.db.models.functions import Replace, JSONObject
from django.contrib.postgres.aggregates import ArrayAgg

from reference_data.models import Omim
from seqr.models import Family, Individual
from seqr.views.utils.airtable_utils import get_airtable_samples
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_search_samples
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.variant_utils import get_variant_main_transcript, get_saved_discovery_variants_by_family, \
    get_variant_inheritance_models, get_sv_name, get_genotype_zygosity

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

INHERITANCE_MODE_MAP = {
    'X-linked': 'X - linked',
    'AR-homozygote': 'Autosomal recessive (homozygous)',
    'AR-comphet': 'Autosomal recessive (compound heterozygous)',
    'de novo': 'de novo',
    'AD': 'Autosomal dominant',
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

FAMILY_ROW_TYPE = 'family'
SUBJECT_ROW_TYPE = 'subject'
SAMPLE_ROW_TYPE = 'sample'
DISCOVERY_ROW_TYPE = 'discovery'


def parse_anvil_metadata(projects, max_loaded_date, user, add_row, omit_airtable=False, family_values=None,
                          get_additional_sample_fields=None, get_additional_variant_fields=None, allow_missing_discovery_genes=False):
    individual_samples = _get_loaded_before_date_project_individual_samples(projects, max_loaded_date)

    family_data = Family.objects.filter(individual__in=individual_samples).distinct().values(
        'id', 'family_id', 'post_discovery_omim_numbers', 'project__name',
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
        **(family_values or {}),
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

    sample_airtable_metadata = None if omit_airtable else _get_sample_airtable_metadata(list(sample_ids), user)

    saved_variants_by_family = _get_parsed_saved_discovery_variants_by_family(list(samples_by_family_id.keys()))
    compound_het_gene_id_by_family, gene_ids = _process_saved_variants(
        saved_variants_by_family, family_individual_affected_guids)
    genes_by_id = get_genes(gene_ids)

    mim_numbers = set()
    for family in family_data:
        mim_numbers.update(family['post_discovery_omim_numbers'])
    mim_decription_map = {
        o.phenotype_mim_number: o.phenotype_description
        for o in Omim.objects.filter(phenotype_mim_number__in=mim_numbers)
    }

    for family_id, family_samples in samples_by_family_id.items():
        saved_variants = saved_variants_by_family[family_id]

        family_subject_row = family_data_by_id[family_id]
        genome_version = family_subject_row.pop('genome_version')

        mim_numbers = family_subject_row.pop('post_discovery_omim_numbers')
        if mim_numbers:
            family_subject_row.update({
                'disease_id': ';'.join(['OMIM:{}'.format(mim_number) for mim_number in mim_numbers]),
                'disease_description': ';'.join([
                    mim_decription_map.get(mim_number, '') for mim_number in mim_numbers]).replace(',', ';'),
            })

        affected_individual_guids, _, male_individual_guids = family_individual_affected_guids[family_id]

        family_consanguinity = any(sample.individual.consanguinity is True for sample in family_samples)
        family_row = {
            'family_id': family_subject_row['family_id'],
            'consanguinity': 'Present' if family_consanguinity else 'None suspected',
        }
        if len(affected_individual_guids) > 1:
            family_row['family_history'] = 'Yes'
        add_row(family_row, family_id, FAMILY_ROW_TYPE)

        parsed_variants = [
            _parse_anvil_family_saved_variant(
                variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id,
                get_additional_variant_fields, allow_missing_discovery_genes,
            )
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
            add_row(subject_row, family_id, SUBJECT_ROW_TYPE)

            sample_row = _get_sample_row(sample, has_dbgap_submission, airtable_metadata, get_additional_sample_fields)
            add_row(sample_row, family_id, SAMPLE_ROW_TYPE)

            discovery_row = _get_discovery_rows(sample, parsed_variants, male_individual_guids)
            add_row(discovery_row, family_id, DISCOVERY_ROW_TYPE)


def _get_nested_variant_name(variant):
    return get_sv_name(variant) if variant.get('svType') else variant['variantId']


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
            variant['main_transcript'] = get_variant_main_transcript(variant)
            if variant['main_transcript']:
                gene_ids.add(variant['main_transcript']['geneId'])

            affected_individual_guids, unaffected_individual_guids, male_individual_guids = family_individual_affected_guids[family_id]
            inheritance_models, potential_compound_het_gene_ids = get_variant_inheritance_models(
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


def _parse_anvil_family_saved_variant(variant, family_id, genome_version, compound_het_gene_id_by_family, genes_by_id,
                                      get_additional_variant_fields, allow_missing_discovery_genes):
    if variant['inheritance_models']:
        inheritance_mode = '|'.join([INHERITANCE_MODE_MAP[model] for model in variant['inheritance_models']])
    else:
        inheritance_mode = 'Unknown / Other'

    parsed_variant = {
        'Gene_Class': 'Known',
        'inheritance_description': inheritance_mode,
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


def _get_sample_row(sample, has_dbgap_submission, airtable_metadata, get_additional_sample_fields=None):
    individual = sample.individual
    sample_row = {
        'subject_id': individual.individual_id,
        'sample_id': sample.sample_id,
    }
    if has_dbgap_submission:
        sample_row['dbgap_sample_id'] = airtable_metadata.get('dbgap_sample_id', '')
    if get_additional_sample_fields:
        sample_row.update(get_additional_sample_fields(sample, airtable_metadata))
    return sample_row


def _get_discovery_rows(sample, parsed_variants, male_individual_guids):
    individual = sample.individual
    discovery_row = {
        'subject_id': individual.individual_id,
        'sample_id': sample.sample_id,
    }
    discovery_rows = []
    for genotypes, parsed_variant in parsed_variants:
        genotype = genotypes.get(individual.guid, {})
        chrom = parsed_variant.get('Chrom', '')
        is_x_linked = "X" in chrom
        zygosity = get_genotype_zygosity(
            genotype, is_hemi_variant=is_x_linked and individual.guid in male_individual_guids)
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
