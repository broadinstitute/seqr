from collections import defaultdict
from elasticsearch_dsl import Index
import json
import logging

from datetime import datetime, timedelta
from dateutil import relativedelta as rdelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import prefetch_related_objects, Q, Prefetch, Max
from django.http.response import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError

from seqr.utils.es_utils import get_es_client
from seqr.utils.file_utils import file_iter
from seqr.utils.gene_utils import get_genes
from seqr.utils.xpos_utils import get_chrom_pos

from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_submissions, parse_mme_features, \
    parse_mme_gene_variants, get_mme_metrics
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.json_utils import create_json_response, _to_camel_case
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, get_json_for_saved_variants, \
    get_json_for_variant_functional_data_tag_types, get_json_for_projects, _get_json_for_families, \
    get_json_for_locus_lists, _get_json_for_models, get_json_for_matchmaker_submissions, \
    get_json_for_saved_variants_with_tags
from seqr.views.utils.proxy_request_utils import proxy_request

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant, Individual, ProjectCategory, \
    LocusList
from reference_data.models import Omim

from settings import ELASTICSEARCH_SERVER, KIBANA_SERVER, API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def elasticsearch_status(request):
    client = get_es_client()

    disk_fields = ['node', 'disk.avail', 'disk.used', 'disk.percent']
    disk_status = [{
        _to_camel_case(field.replace('.', '_')): disk[field] for field in disk_fields
    } for disk in client.cat.allocation(format="json", h=','.join(disk_fields))]

    index_fields = ['index', 'docs.count', 'store.size', 'creation.date.string']
    indices = [{
        _to_camel_case(field.replace('.', '_')): index[field] for field in index_fields
    } for index in client.cat.indices(format="json", h=','.join(index_fields))
        if all(not index['index'].startswith(omit_prefix) for omit_prefix in ['.', 'index_operations_log'])]

    aliases = defaultdict(list)
    for alias in client.cat.aliases(format="json", h='alias,index'):
        aliases[alias['alias']].append(alias['index'])

    mappings = Index('_all', using=client).get_mapping(doc_type='variant')

    active_samples = Sample.objects.filter(
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        is_active=True,
        elasticsearch_index__isnull=False,
    ).prefetch_related('individual', 'individual__family')
    prefetch_related_objects(active_samples, 'individual__family__project')
    seqr_index_projects = defaultdict(lambda: defaultdict(set))
    es_projects = set()
    for sample in active_samples:
        for index_name in sample.elasticsearch_index.split(','):
            project = sample.individual.family.project
            es_projects.add(project)
            if index_name in aliases:
                for aliased_index_name in aliases[index_name]:
                    seqr_index_projects[aliased_index_name][project].add(sample.individual.guid)
            else:
                seqr_index_projects[index_name.rstrip('*')][project].add(sample.individual.guid)

    for index in indices:
        index_name = index['index']
        index_mapping = mappings[index_name]['mappings']['variant']
        index.update(index_mapping.get('_meta', {}))

        projects_for_index = []
        for index_prefix in seqr_index_projects.keys():
            if index_name.startswith(index_prefix):
                projects_for_index += seqr_index_projects.pop(index_prefix).keys()
        index['projects'] = [{'projectGuid': project.guid, 'projectName': project.name} for project in projects_for_index]

    errors = ['{} does not exist and is used by project(s) {}'.format(
        index, ', '.join(['{} ({} samples)'.format(p.name, len(indivs)) for p, indivs in project_individuals.items()])
    ) for index, project_individuals in seqr_index_projects.items() if project_individuals]

    return create_json_response({
        'indices': indices,
        'diskStats': disk_status,
        'elasticsearchHost': ELASTICSEARCH_SERVER,
        'errors': errors,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def mme_details(request):
    submissions = MatchmakerSubmission.objects.filter(deleted_date__isnull=True)

    hpo_terms_by_id, genes_by_id, gene_symbols_to_ids = get_mme_genes_phenotypes_for_submissions(submissions)

    submission_json = get_json_for_matchmaker_submissions(
        submissions, additional_model_fields=['label'], all_parent_guids=True)
    submissions_by_guid = {s['submissionGuid']: s for s in submission_json}

    for submission in submissions:
        gene_variants = parse_mme_gene_variants(submission.genomic_features, gene_symbols_to_ids)
        submissions_by_guid[submission.guid].update({
            'phenotypes': parse_mme_features(submission.features, hpo_terms_by_id),
            'geneVariants': gene_variants,
            'geneSymbols': ','.join({genes_by_id.get(gv['geneId'], {}).get('geneSymbol') for gv in gene_variants})
        })

    return create_json_response({
        'metrics': get_mme_metrics(),
        'submissions': submissions_by_guid.values(),
        'genesById': genes_by_id,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def seqr_stats(request):

    families_count = Family.objects.only('family_id').distinct('family_id').count()
    individuals_count = Individual.objects.only('individual_id').distinct('individual_id').count()

    sample_counts = defaultdict(set)
    for sample in Sample.objects.filter(is_active=True).only('sample_id', 'sample_type'):
        sample_counts[sample.sample_type].add(sample.sample_id)

    for sample_type, sample_ids_set in sample_counts.items():
        sample_counts[sample_type] = len(sample_ids_set)

    return create_json_response({
        'familyCount': families_count,
        'individualCount': individuals_count,
        'sampleCountByType': sample_counts,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def anvil_export(request, project_guid):
    if project_guid == 'all':
        project_guid = None

    if project_guid:
        projects_by_guid = {project_guid: Project.objects.get(guid=project_guid)}
    else:
        projects_by_guid = {p.guid: p for p in Project.objects.filter(projectcategory__name__iexact='anvil')}

    individuals = _get_loaded_before_date_project_individuals(projects_by_guid.values(), loaded_before=request.GET.get('loadedBefore'))

    saved_variants_by_family = _get_saved_variants_by_family(projects_by_guid.values())

    # Handle compound het genes
    compound_het_gene_id_by_family = {}
    for family_guid, saved_variants in saved_variants_by_family.items():
        if len(saved_variants) > 1:
            potential_compound_het_variants = [
                variant for variant in saved_variants if all(gen['numAlt'] < 2 for gen in variant['genotypes'].values())
            ]
            main_gene_ids = {_get_variant_main_transcript(variant)['geneId'] for variant in potential_compound_het_variants}
            if len(main_gene_ids) > 1:
                # This occurs in compound hets where some hits have a primary transcripts in different genes
                for gene_id in main_gene_ids:
                    if all(gene_id in variant['transcripts'] for variant in potential_compound_het_variants):
                        compound_het_gene_id_by_family[family_guid] = gene_id

    rows = _get_json_for_individuals(list(individuals), project_guid=project_guid, family_fields=['family_id', 'coded_phenotype'])

    gene_ids = set()
    for row in rows:
        row['Project_ID'] = projects_by_guid[row['projectGuid']].name

        saved_variants = saved_variants_by_family[row['familyGuid']]
        row['numSavedVariants'] = len(saved_variants)
        for i, variant in enumerate(saved_variants):
            main_transcript = _get_variant_main_transcript(variant)
            genotype = variant['genotypes'].get(row['individualGuid'], {})
            if genotype.get('numAlt', -1) > 0:
                gene_id = compound_het_gene_id_by_family.get(row['familyGuid']) or main_transcript['geneId']
                gene_ids.add(gene_id)
                variant_fields = {
                    'Zygosity': 'heterozygous' if genotype['numAlt'] == 1 else 'homozygous',
                    'Chrom': variant['chrom'],
                    'Pos': variant['pos'],
                    'Ref': variant['ref'],
                    'Alt': variant['alt'],
                    'hgvsc': main_transcript['hgvsc'],
                    'hgvsp': main_transcript['hgvsp'],
                    'Transcript': main_transcript['transcriptId'],
                    'geneId': gene_id,
                }
                row.update({'{}-{}'.format(k, i + 1): v for k, v in variant_fields.items()})

    genes_by_id = get_genes(gene_ids)
    for row in rows:
        for key, gene_id in row.items():
            if key.startswith('geneId') and genes_by_id.get(gene_id):
                row[key.replace('geneId', 'Gene')] = genes_by_id[gene_id]['geneSymbol']

    return create_json_response({'anvilRows': rows})


def _get_variant_main_transcript(variant):
    main_transcript_id = variant.get('selectedMainTranscriptId') or variant.get('mainTranscriptId')
    if not main_transcript_id:
        return {}
    for transcripts in variant.get('transcripts', {}).values():
        main_transcript = next((t for t in transcripts if t['transcriptId'] == main_transcript_id), None)
        if main_transcript:
            return main_transcript


def _get_loaded_before_date_project_individuals(projects, loaded_before=None):
    if loaded_before:
        max_loaded_date = datetime.strptime(loaded_before, '%Y-%m-%d')
    else:
        max_loaded_date = datetime.now() - timedelta(days=365)
    loaded_samples = Sample.objects.filter(
        individual__family__project__in=projects,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        loaded_date__isnull=False,
        loaded_date__lte=max_loaded_date,
    ).select_related('individual__family__project').order_by('loaded_date')
    return list({sample.individual for sample in loaded_samples})


def _get_saved_variants_by_family(projects):
    tag_type = VariantTagType.objects.get(name='Known gene for phenotype')

    project_saved_variants = SavedVariant.objects.select_related('family').filter(
        family__project__in=projects,
        varianttag__variant_tag_type=tag_type,
    )

    project_saved_variants_json = get_json_for_saved_variants(project_saved_variants, add_details=True)

    saved_variants_by_family = defaultdict(list)
    for variant in project_saved_variants_json:
        for family_guid in variant['familyGuids']:
            saved_variants_by_family[family_guid].append(variant)

    return saved_variants_by_family


# HPO categories are direct children of HP:0000118 "Phenotypic abnormality".
# See http://compbio.charite.de/hpoweb/showterm?id=HP:0000118
HPO_CATEGORY_NAMES = {
    'HP:0000478': 'Eye Defects',
    'HP:0025142': 'Constitutional Symptom',
    'HP:0002664': 'Neoplasm',
    'HP:0000818': 'Endocrine System',
    'HP:0000152': 'Head or Neck',
    'HP:0002715': 'Immune System',
    'HP:0001507': 'Growth',
    'HP:0045027': 'Thoracic Cavity',
    'HP:0001871': 'Blood',
    'HP:0002086': 'Respiratory',
    'HP:0000598': 'Ear Defects',
    'HP:0001939': 'Metabolism/Homeostasis',
    'HP:0003549': 'Connective Tissue',
    'HP:0001608': 'Voice',
    'HP:0000707': 'Nervous System',
    'HP:0000769': 'Breast',
    'HP:0001197': 'Prenatal development or birth',
    'HP:0040064': 'Limbs',
    'HP:0025031': 'Abdomen',
    'HP:0003011': 'Musculature',
    'HP:0001626': 'Cardiovascular System',
    'HP:0000924': 'Skeletal System',
    'HP:0500014': 'Test Result',
    'HP:0001574': 'Integument',
    'HP:0000119': 'Genitourinary System',
    'HP:0025354': 'Cellular Phenotype',
}

DEFAULT_ROW = row = {
    "t0": None,
    "t0_copy": None,
    "months_since_t0": None,
    "sample_source": "CMG",
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
DEFAULT_ROW.update({hpo_category: 'N' for hpo_category in [
    "connective_tissue",
    "voice",
    "nervous_system",
    "breast",
    "eye_defects",
    "prenatal_development_or_birth",
    "neoplasm",
    "endocrine_system",
    "head_or_neck",
    "immune_system",
    "growth",
    "limbs",
    "thoracic_cavity",
    "blood",
    "musculature",
    "cardiovascular_system",
    "abdomen",
    "skeletal_system",
    "respiratory",
    "ear_defects",
    "metabolism_homeostasis",
    "genitourinary_system",
    "integument",
]})

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


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def get_projects_for_category(request, project_category_name):
    category = ProjectCategory.objects.get(name=project_category_name)
    return create_json_response({
        'projectGuids': [p.guid for p in Project.objects.filter(projectcategory=category).only('guid')],
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def discovery_sheet(request, project_guid):
    errors = []

    project = Project.objects.filter(guid=project_guid).prefetch_related(
        Prefetch('family_set', to_attr='families', queryset=Family.objects.prefetch_related('individual_set'))
    ).distinct().first()
    if not project:
        raise Exception('Invalid project {}'.format(project_guid))

    loaded_samples_by_project_family = _get_loaded_samples_by_project_family([project])
    saved_variants_by_project_family = _get_saved_variants_by_project_family([project])
    rows = _generate_rows(project, loaded_samples_by_project_family, saved_variants_by_project_family, errors)

    return create_json_response({
        'rows': rows,
        'errors': errors,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def success_story(request, success_story_types):
    if success_story_types == 'all':
        families = Family.objects.filter(success_story__isnull=False)
    else:
        success_story_types = success_story_types.split(',')
        families = Family.objects.filter(success_story_types__overlap=success_story_types)

    rows = [{
        "project_guid": family.project.guid,
        "family_guid": family.guid,
        "family_id": family.family_id,
        "success_story_types": family.success_story_types,
        "success_story": family.success_story,
        "row_id": family.guid,
    } for family in families]

    return create_json_response({
        'rows': rows,
    })


def _get_loaded_samples_by_project_family(projects):
    loaded_samples = Sample.objects.filter(
        individual__family__project__in=projects,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        loaded_date__isnull=False
    ).select_related('individual__family__project').order_by('loaded_date')

    loaded_samples_by_project_family = defaultdict(lambda:  defaultdict(list))
    for sample in loaded_samples:
        family = sample.individual.family
        loaded_samples_by_project_family[family.project.guid][family.guid].append(sample)

    return loaded_samples_by_project_family


def _get_saved_variants_by_project_family(projects):
    tag_types = VariantTagType.objects.filter(project__isnull=True, category='CMG Discovery Tags')

    project_saved_variants = SavedVariant.objects.select_related('family').prefetch_related(
        Prefetch('varianttag_set', to_attr='discovery_tags',
                 queryset=VariantTag.objects.filter(variant_tag_type__in=tag_types).select_related('variant_tag_type'),
                 )).prefetch_related('variantfunctionaldata_set').filter(
        family__project__in=projects,
        varianttag__variant_tag_type__in=tag_types,
    )

    saved_variants_by_project_family =  defaultdict(lambda:  defaultdict(list))
    for saved_variant in project_saved_variants:
        saved_variants_by_project_family[saved_variant.family.project.guid][saved_variant.family.guid].append(saved_variant)

    return saved_variants_by_project_family


def _generate_rows(project, loaded_samples_by_project_family, saved_variants_by_project_family, errors):
    rows = []

    loaded_samples_by_family = loaded_samples_by_project_family[project.guid]
    saved_variants_by_family = saved_variants_by_project_family[project.guid]

    if not loaded_samples_by_family:
        errors.append("No data loaded for project: %s" % project)
        logger.info("No data loaded for project: %s" % project)
        return []

    if "external" in project.name or "reprocessed" in project.name:
        sequencing_approach = "REAN"
    else:
        sequencing_approach = loaded_samples_by_family.values()[0][-1].sample_type

    now = timezone.now()
    for family in project.families:
        samples = loaded_samples_by_family.get(family.guid)
        if not samples:
            errors.append("No data loaded for family: %s. Skipping..." % family)
            continue

        row = {
            "project_guid": project.guid,
            "family_guid": family.guid,
            "family_id": family.family_id,
            "collaborator": project.name,
            "sequencing_approach": sequencing_approach,
            "extras_pedigree_url": family.pedigree_image.url if family.pedigree_image else "",
            "coded_phenotype": family.coded_phenotype or "",
            "pubmed_ids": '; '.join(family.pubmed_ids),
            "analysis_summary": (family.analysis_summary or '').strip('" \n'),
            "row_id": family.guid,
            "num_individuals_sequenced": len({sample.individual for sample in samples})
        }
        row.update(DEFAULT_ROW)

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

        submitted_to_mme = any(i.mme_submitted_date for i in family.individual_set.all())
        if submitted_to_mme:
            row["submitted_to_mme"] = "Y"

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in family.individual_set.all() if i.phenotips_data]

        phenotips_individual_expected_inheritance_model = [
            inheritance_mode["label"] for phenotips_data in phenotips_individual_data_records for inheritance_mode in phenotips_data.get("global_mode_of_inheritance", [])
        ]
        if len(phenotips_individual_expected_inheritance_model) == 1:
            row["expected_inheritance_model"] = phenotips_individual_expected_inheritance_model.pop()

        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        omim_number_initial = next((disorder["id"] for disorders in phenotips_individual_mim_disorders for disorder in disorders if "id" in disorder), '').replace("MIM:", "")
        if omim_number_initial:
            row.update({
                "omim_number_initial": omim_number_initial,
                "phenotype_class": "KNOWN",
            })

        if family.post_discovery_omim_number:
            row["omim_number_post_discovery"] = family.post_discovery_omim_number

        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        category_not_set_on_some_features = False
        for features_list in phenotips_individual_features:
            for feature in features_list:
                if "category" not in feature:
                    category_not_set_on_some_features = True
                    continue

                if feature["observed"].lower() == "yes":
                    hpo_category_id = feature["category"]
                    hpo_category_name = HPO_CATEGORY_NAMES[hpo_category_id]
                    key = hpo_category_name.lower().replace(" ", "_").replace("/", "_")

                    row[key] = "Y"
                elif feature["observed"].lower() == "no":
                    continue
                else:
                    raise ValueError("Unexpected value for 'observed' in %s" % (feature,))

        if category_not_set_on_some_features:
            errors.append("HPO category field not set for some HPO terms in %s" % family)

        saved_variants = saved_variants_by_family.get(family.guid)
        if not saved_variants:
            rows.append(row)
            continue

        for variant in saved_variants:
            if not variant.saved_variant_json:
                errors.append("%s - variant annotation not found" % variant)
                rows.append(row)
                continue

            if not variant.saved_variant_json['transcripts']:
                errors.append("%s - no gene ids" % variant)
                rows.append(row)
                continue

        affected_individual_guids = set()
        unaffected_individual_guids = set()
        for sample in samples:
            if sample.individual.affected == "A":
                affected_individual_guids.add(sample.individual.guid)
            elif sample.individual.affected == "N":
                unaffected_individual_guids.add(sample.individual.guid)

        potential_compound_het_genes = defaultdict(set)
        for variant in saved_variants:
            inheritance_models = set()

            affected_indivs_with_hom_alt_variants = set()
            affected_indivs_with_het_variants = set()
            unaffected_indivs_with_hom_alt_variants = set()
            unaffected_indivs_with_het_variants = set()
            is_x_linked = False

            genotypes = variant.saved_variant_json.get('genotypes')
            if genotypes:
                chrom = variant.saved_variant_json['chrom']
                is_x_linked = "X" in chrom
                for sample_guid, genotype in genotypes.items():
                    if genotype["numAlt"] == 2 and sample_guid in affected_individual_guids:
                        affected_indivs_with_hom_alt_variants.add(sample_guid)
                    elif genotype["numAlt"] == 1 and sample_guid in affected_individual_guids:
                        affected_indivs_with_het_variants.add(sample_guid)
                    elif genotype["numAlt"] == 2 and sample_guid in unaffected_individual_guids:
                        unaffected_indivs_with_hom_alt_variants.add(sample_guid)
                    elif genotype["numAlt"] == 1 and sample_guid in unaffected_individual_guids:
                        unaffected_indivs_with_het_variants.add(sample_guid)

            # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
            if not unaffected_indivs_with_hom_alt_variants and affected_indivs_with_hom_alt_variants:
                if is_x_linked:
                    inheritance_models.add("X-linked")
                else:
                    inheritance_models.add("AR-homozygote")

            if not unaffected_indivs_with_hom_alt_variants and not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
                if unaffected_individual_guids:
                    inheritance_models.add("de novo")
                else:
                    inheritance_models.add("AD")

            if not unaffected_indivs_with_hom_alt_variants and (len(
                    unaffected_individual_guids) < 2 or unaffected_indivs_with_het_variants) and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants:
                for gene_id in variant.saved_variant_json['transcripts']:
                    potential_compound_het_genes[gene_id].add(variant)

            variant.saved_variant_json['inheritance'] = inheritance_models

            main_transcript_id = variant.selected_main_transcript_id or variant.saved_variant_json.get('mainTranscriptId')
            if main_transcript_id:
                for gene_id, transcripts in variant.saved_variant_json['transcripts'].items():
                    if any(t['transcriptId'] == main_transcript_id for t in transcripts):
                        variant.saved_variant_json['mainTranscriptGeneId'] = gene_id
                        break
            elif len(variant.saved_variant_json['transcripts']) == 1 and not variant.saved_variant_json['transcripts'].values()[0]:
                variant.saved_variant_json['mainTranscriptGeneId'] = variant.saved_variant_json['transcripts'].keys()[0]

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
                        variant.saved_variant_json['mainTranscriptGeneId'] for variant in variants
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
                gene_id = variant.saved_variant_json['mainTranscriptGeneId']
                gene_ids_to_saved_variants[gene_id].add(variant)
                gene_ids_to_variant_tag_names[gene_id].update({vt.variant_tag_type.name for vt in variant.discovery_tags})
                gene_ids_to_inheritance[gene_id].update(variant.saved_variant_json['inheritance'])

        if len(gene_ids_to_saved_variants) > 1:
            row["gene_count"] = len(gene_ids_to_saved_variants)

        for gene_id, variants in gene_ids_to_saved_variants.items():
            # create a copy of the row dict
            row = dict(row)

            row["actual_inheritance_model"] = ", ".join(gene_ids_to_inheritance[gene_id])

            row["gene_id"] = gene_id
            row["row_id"] += gene_id

            variant_tag_names = gene_ids_to_variant_tag_names[gene_id]

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
                    "posted_publicly":  "",
                    "analysis_complete_status": "complete",
                    "novel_mendelian_gene":  "Y" if any("Novel gene" in name for name in variant_tag_names) else "N",
                })

                if has_known_gene_for_phenotype:
                    row["phenotype_class"] = "KNOWN"
                elif any(tag in variant_tag_names for tag in [
                    'Tier 1 - Known gene, new phenotype', 'Tier 2 - Known gene, new phenotype',
                ]):
                    row["phenotype_class"] = "NEW"
                elif any(tag in variant_tag_names for tag in [
                    'Tier 1 - Phenotype expansion', 'Tier 1 - Novel mode of inheritance',  'Tier 2 - Phenotype expansion',
                ]):
                    row["phenotype_class"] = "EXPAN"
                elif any(tag in variant_tag_names for tag in [
                    'Tier 1 - Phenotype not delineated', 'Tier 2 - Phenotype not delineated'
                ]):
                    row["phenotype_class"] = "UE"

            if not submitted_to_mme:
                if has_tier1 or has_tier2:
                    row["submitted_to_mme"] = "N" if t0_months_since_t0 > 7 else "TBD"
                elif has_known_gene_for_phenotype:
                    row["submitted_to_mme"] = "KPG"

            if has_tier1 or has_tier2:
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
                        functional_field = FUNCTIONAL_DATA_FIELD_MAP[f.functional_data_tag]
                        if functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                            value = f.metadata
                            if functional_field == ADDITIONAL_KINDREDS_FIELD:
                                value = str(int(value) + 1)
                            elif functional_field == OVERLAPPING_KINDREDS_FIELD:
                                existing_val = row[functional_field]
                                if existing_val != 'NA':
                                    value = str(max(int(existing_val), int(value)))
                            elif row[functional_field] != 'NS':
                                value = '{} {}'.format(row[functional_field], value)
                        else:
                            value = 'Y'

                        row[functional_field] = value
            elif has_known_gene_for_phenotype:
                for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
                    row[functional_field] = "KPG"

            row["extras_variant_tag_list"] = []
            for variant in variants:
                variant_id = "-".join(map(str, list(get_chrom_pos(variant.xpos_start)) + [variant.ref, variant.alt]))
                row["extras_variant_tag_list"] += [
                    (variant_id, gene_id, vt.variant_tag_type.name.lower()) for vt in variant.discovery_tags
                ]

            rows.append(row)

    _update_gene_symbols(rows)
    _update_initial_omim_numbers(rows)

    return rows


def _update_gene_symbols(rows):
    genes_by_id = get_genes({row['gene_id'] for row in rows if row.get('gene_id')})
    for row in rows:
        if row.get('gene_id') and genes_by_id.get(row['gene_id']):
            row['gene_name'] = genes_by_id[row['gene_id']]['geneSymbol']

        row["extras_variant_tag_list"] = ["{variant_id}  {gene_symbol}  {tag}".format(
            variant_id=variant_id, gene_symbol=genes_by_id.get(gene_id, {}).get('geneSymbol'), tag=tag,
        ) for variant_id, gene_id, tag in row.get("extras_variant_tag_list", [])]


def _update_initial_omim_numbers(rows):
    omim_numbers = {row['omim_number_initial'] for row in rows if row['omim_number_initial'] and row['omim_number_initial'] != 'NA'}

    omim_number_map = {str(omim.phenotype_mim_number): omim.phenotypic_series_number
                       for omim in Omim.objects.filter(phenotype_mim_number__in=omim_numbers, phenotypic_series_number__isnull=False)}

    for mim_number, phenotypic_series_number in omim_number_map.items():
        logger.info("Will replace OMIM initial # %s with phenotypic series %s" % (mim_number, phenotypic_series_number))

    for row in rows:
        if omim_number_map.get(row['omim_number_initial']):
            row['omim_number_initial'] = omim_number_map[row['omim_number_initial']]


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def saved_variants(request, tag):
    gene = request.GET.get('gene')
    tag_type = VariantTagType.objects.get(name=tag, project__isnull=True)
    saved_variant_models = SavedVariant.objects.filter(varianttag__variant_tag_type=tag_type)
    if gene:
        saved_variant_models = saved_variant_models.filter(saved_variant_json__transcripts__has_key=gene)

    if saved_variant_models.count() > 10000 and not gene:
        return create_json_response({'message': 'Select a gene to filter variants'}, status=400)

    prefetch_related_objects(saved_variant_models, 'family__project')
    response_json = get_json_for_saved_variants_with_tags(saved_variant_models, add_details=True)

    project_models_by_guid = {variant.family.project.guid: variant.family.project for variant in saved_variant_models}
    families = {variant.family for variant in saved_variant_models}
    individuals = Individual.objects.filter(family__in=families)

    genes = _saved_variant_genes(response_json['savedVariantsByGuid'].values())
    locus_list_guids = _add_locus_lists(project_models_by_guid.values(), saved_variants, genes)

    projects_json = get_json_for_projects(project_models_by_guid.values(), user=request.user, add_project_category_guids_field=False)
    functional_tag_types = get_json_for_variant_functional_data_tag_types()

    variant_tag_types = VariantTagType.objects.filter(Q(project__in=project_models_by_guid.values()) | Q(project__isnull=True))
    prefetch_related_objects(variant_tag_types, 'project')
    variant_tags_json = _get_json_for_models(variant_tag_types)
    tag_projects = {vt.guid: vt.project.guid for vt in variant_tag_types if vt.project}

    for project_json in projects_json:
        project_guid = project_json['projectGuid']
        project_variant_tags = [
            vt for vt in variant_tags_json if tag_projects.get(vt['variantTagTypeGuid'], project_guid) == project_guid]
        project_json.update({
            'locusListGuids': locus_list_guids,
            'variantTagTypes': sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order']),
            'variantFunctionalTagTypes': functional_tag_types,
        })

    families_json = _get_json_for_families(list(families), user=request.user, add_individual_guids_field=True)
    individuals_json = _get_json_for_individuals(individuals, user=request.user)
    locus_lists_by_guid = {locus_list['locusListGuid']: locus_list for locus_list in
                           get_json_for_locus_lists(LocusList.objects.filter(guid__in=locus_list_guids), request.user)}

    response_json.update({
        'genesById': genes,
        'projectsByGuid': {project['projectGuid']: project for project in projects_json},
        'familiesByGuid': {family['familyGuid']: family for family in families_json},
        'individualsByGuid': {indiv['individualGuid']: indiv for indiv in individuals_json},
        'locusListsByGuid': locus_lists_by_guid,
    })
    return create_json_response(response_json)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def upload_qc_pipeline_output(request):
    file_path = json.loads(request.body)['file']
    raw_records = parse_file(file_path, file_iter(file_path))

    json_records = [dict(zip(raw_records[0], row)) for row in raw_records[1:]]

    missing_columns = [field for field in ['seqr_id', 'data_type', 'filter_flags', 'qc_metrics_filters', 'qc_pop']
                       if field not in json_records[0]]
    if missing_columns:
        message = 'The following required columns are missing: {}'.format(', '.join(missing_columns))
        return create_json_response({'errors': [message]}, status=400, reason=message)

    dataset_types = {record['data_type'].lower() for record in json_records if record['data_type'].lower() != 'n/a'}
    if len(dataset_types) == 0:
        message = 'No dataset type detected'
        return create_json_response({'errors': [message]}, status=400, reason=message)
    elif len(dataset_types) > 1:
        message = 'Multiple dataset types detected: {}'.format(' ,'.join(dataset_types))
        return create_json_response({'errors': [message]}, status=400, reason=message)
    elif list(dataset_types)[0] not in DATASET_TYPE_MAP:
        message = 'Unexpected dataset type detected: "{}" (should be "exome" or "genome")'.format(list(dataset_types)[0])
        return create_json_response({'errors': [message]}, status=400, reason=message)

    dataset_type = DATASET_TYPE_MAP[list(dataset_types)[0]]

    info_message = 'Parsed {} {} samples'.format(len(json_records), dataset_type)
    logger.info(info_message)
    info = [info_message]
    warnings = []

    sample_ids = {record['seqr_id'] for record in json_records}
    samples = Sample.objects.filter(
        sample_id__in=sample_ids,
        sample_type=Sample.SAMPLE_TYPE_WES if dataset_type == 'exome' else Sample.SAMPLE_TYPE_WGS,
    ).exclude(
        individual__family__project__name__in=EXCLUDE_PROJECTS
    ).exclude(individual__family__project__projectcategory__name=EXCLUDE_PROJECT_CATEGORY)

    sample_individuals = {
        agg['sample_id']: agg['individuals'] for agg in
        samples.values('sample_id').annotate(individuals=ArrayAgg('individual_id', distinct=True))
    }

    sample_individual_max_loaded_date = {
        agg['individual_id']: agg['max_loaded_date'] for agg in
        samples.values('individual_id').annotate(max_loaded_date=Max('loaded_date'))
    }
    individual_latest_sample_id = {
        s.individual_id: s.sample_id for s in samples
        if s.loaded_date == sample_individual_max_loaded_date.get(s.individual_id)
    }

    for record in json_records:
        record['individual_ids'] = list({
            individual_id for individual_id in sample_individuals.get(record['seqr_id'], [])
            if individual_latest_sample_id[individual_id] == record['seqr_id']
        })

    missing_sample_ids = {record['seqr_id'] for record in json_records if not record['individual_ids']}
    if missing_sample_ids:
        individuals = Individual.objects.filter(individual_id__in=missing_sample_ids).exclude(
            family__project__name__in=EXCLUDE_PROJECTS).exclude(
            family__project__projectcategory__name=EXCLUDE_PROJECT_CATEGORY).exclude(
            sample__sample_type=Sample.SAMPLE_TYPE_WGS if dataset_type == 'exome' else Sample.SAMPLE_TYPE_WES)
        individual_db_ids_by_id = defaultdict(list)
        for individual in individuals:
            individual_db_ids_by_id[individual.individual_id].append(individual.id)
        for record in json_records:
            if not record['individual_ids'] and len(individual_db_ids_by_id[record['seqr_id']]) == 1:
                record['individual_ids'] = individual_db_ids_by_id[record['seqr_id']]
                missing_sample_ids.remove(record['seqr_id'])

    multi_individual_samples = {record['seqr_id']: len(record['individual_ids'])
                                for record in json_records if len(record['individual_ids']) > 1}
    if multi_individual_samples:
        logger.info('Found {} multi-individual samples from qc output'.format(len(multi_individual_samples)))
        warnings.append('The following {} samples were added to multiple individuals: {}'.format(
            len(multi_individual_samples), ', '.join(
                sorted(['{} ({})'.format(sample_id, count) for sample_id, count in multi_individual_samples.items()]))))

    if missing_sample_ids:
        logger.info('Missing {} samples from qc output'.format(len(missing_sample_ids)))
        warnings.append('The following {} samples were skipped: {}'.format(
            len(missing_sample_ids), ', '.join(sorted(list(missing_sample_ids)))))

    unknown_filter_flags = set()
    unknown_pop_filter_flags = set()

    inidividuals_by_population = defaultdict(list)
    for record in json_records:
        filter_flags = {}
        for flag in json.loads(record['filter_flags']):
            flag = '{}_{}'.format(flag, dataset_type) if flag == 'coverage' else flag
            flag_col = FILTER_FLAG_COL_MAP.get(flag, flag)
            if flag_col in record:
                filter_flags[flag] = record[flag_col]
            else:
                unknown_filter_flags.add(flag)

        pop_platform_filters = {}
        for flag in json.loads(record['qc_metrics_filters']):
            flag_col = 'sample_qc.{}'.format(flag)
            if flag_col in record:
                pop_platform_filters[flag] = record[flag_col]
            else:
                unknown_pop_filter_flags.add(flag)

        if filter_flags or pop_platform_filters:
            Individual.objects.filter(id__in=record['individual_ids']).update(
                filter_flags=filter_flags or None, pop_platform_filters=pop_platform_filters or None)

        inidividuals_by_population[record['qc_pop'].upper()] += record['individual_ids']

    for population, indiv_ids in inidividuals_by_population.items():
        Individual.objects.filter(id__in=indiv_ids).update(population=population)

    if unknown_filter_flags:
        message = 'The following filter flags have no known corresponding value and were not saved: {}'.format(
            ', '.join(unknown_filter_flags))
        logger.info(message)
        warnings.append(message)

    if unknown_pop_filter_flags:
        message = 'The following population platform filters have no known corresponding value and were not saved: {}'.format(
            ', '.join(unknown_pop_filter_flags))
        logger.info(message)
        warnings.append(message)

    message = 'Found and updated matching seqr individuals for {} samples'.format(len(json_records) - len(missing_sample_ids))
    info.append(message)
    logger.info(message)

    return create_json_response({
        'errors': [],
        'warnings': warnings,
        'info': info,
    })


FILTER_FLAG_COL_MAP = {
    'callrate': 'filtered_callrate',
    'contamination': 'PCT_CONTAMINATION',
    'chimera': 'AL_PCT_CHIMERAS',
    'coverage_exome': 'HS_PCT_TARGET_BASES_20X',
    'coverage_genome': 'WGS_MEAN_COVERAGE'
}

DATASET_TYPE_MAP = {
    'exome': 'exome',
    'genome': 'genome',
    'wes': 'exome',
    'wgs': 'genome',
}

EXCLUDE_PROJECTS = [
    '[DISABLED_OLD_CMG_Walsh_WES]', 'Old Engle Lab All Samples 352S', 'Old MEEI Engle Samples',
    'kl_temp_manton_orphan-diseases_cmg-samples_exomes_v1', 'Interview Exomes',
]
EXCLUDE_PROJECT_CATEGORY = 'Demo'


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def proxy_to_kibana(request):
    try:
        return proxy_request(request, host=KIBANA_SERVER, url=request.get_full_path(), data=request.body, stream=True)
        # use stream=True because kibana returns gziped responses, and this prevents the requests module from
        # automatically unziping them
    except ConnectionError as e:
        logger.error(e)
        return HttpResponse("Error: Unable to connect to Kibana {}".format(e))
