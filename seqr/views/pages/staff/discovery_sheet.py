from collections import defaultdict
import collections
import json
import logging
import re
import requests
import tempfile
import openpyxl as xl

from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail.message import EmailMultiAlternatives
from django.utils import timezone

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL

from seqr.utils.gene_utils import get_genes
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.variant_utils import variant_main_transcript
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from seqr.models import Project, Family, VariantTag, VariantTagType, Sample, SavedVariant, ProjectCategory
from dateutil import relativedelta as rdelta
from django.db.models import Q, Prefetch
from django.shortcuts import render
from settings import SEQR_ID_TO_MME_ID_MAP
from seqr.views.utils.orm_to_json_utils import _get_json_for_project

logger = logging.getLogger(__name__)


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
    "pubmed_ids": "",
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
FUNCTIONAL_DATA_FIELD_MAP = {
    "Additional Unrelated Kindreds w/ Causal Variants in Gene": ADDITIONAL_KINDREDS_FIELD,
    "Genome-wide Linkage": "genome_wide_linkage",
    "Bonferroni corrected p-value": "p_value",
    "Kindreds w/ Overlapping SV & Similar Phenotype": "n_kindreds_overlapping_sv_similar_phenotype",
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
    "n_kindreds_overlapping_sv_similar_phenotype",
    ADDITIONAL_KINDREDS_FIELD,
}


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def get_projects_for_category(request, project_category_name):
    category = ProjectCategory.objects.get(name=project_category_name)
    return create_json_response({
        'projectGuids': [p.guid for p in Project.objects.filter(projectcategory=category).only('guid')],
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
def discovery_sheet(request, project_guid=None):
    rows = []
    errors = []

    # all cmg projects
    if project_guid == 'all':
        logger.info("exporting discovery sheet for all projects")
        projects = Project.objects.filter(projectcategory__name__iexact='cmg').prefetch_related(
            Prefetch('family_set', to_attr='families', queryset=Family.objects.prefetch_related('individual_set'))
        ).distinct()

        loaded_samples_by_project_family = get_loaded_samples_by_project_family(projects)
        saved_variants_by_project_family = get_saved_variants_by_project_family(projects)
        for project in projects:
            rows.extend(generate_rows(
                project, loaded_samples_by_project_family, saved_variants_by_project_family, errors,
                update_omim_and_gene_symbols=False,
            ))

        _update_gene_symbols(rows)
        _update_initial_omim_numbers(rows)

    else:
        # generate table for 1 project
        project = Project.objects.filter(guid=project_guid).prefetch_related(
            Prefetch('family_set', to_attr='families', queryset=Family.objects.prefetch_related('individual_set'))
        ).distinct().first()
        if not project:
            raise Exception('Invalid project {}'.format(project_guid))

        loaded_samples_by_project_family = get_loaded_samples_by_project_family([project])
        saved_variants_by_project_family = get_saved_variants_by_project_family([project])
        rows = generate_rows(project, loaded_samples_by_project_family, saved_variants_by_project_family, errors)

    return create_json_response({
        'rows': rows,
        'errors': errors,
    })


def get_loaded_samples_by_project_family(projects):
    loaded_samples = Sample.objects.filter(
        individual__family__project__in=projects,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_status=Sample.SAMPLE_STATUS_LOADED,
        loaded_date__isnull=False
    ).select_related('individual__family__project').order_by('loaded_date')

    loaded_samples_by_project_family = collections.defaultdict(lambda: collections.defaultdict(list))
    for sample in loaded_samples:
        family = sample.individual.family
        loaded_samples_by_project_family[family.project.guid][family.guid].append(sample)

    return loaded_samples_by_project_family


def get_saved_variants_by_project_family(projects):
    tag_types = VariantTagType.objects.filter(Q(project__isnull=True) & (Q(category='CMG Discovery Tags') | Q(name='Share with KOMP')))

    project_saved_variants = SavedVariant.objects.select_related('project').select_related('family').prefetch_related(
        Prefetch('varianttag_set', to_attr='discovery_tags',
                 queryset=VariantTag.objects.filter(variant_tag_type__in=tag_types).select_related('variant_tag_type'),
                 )).prefetch_related('variantfunctionaldata_set').filter(
        project__in=projects,
        varianttag__variant_tag_type__in=tag_types,
    )

    saved_variants_by_project_family = collections.defaultdict(lambda: collections.defaultdict(list))
    for saved_variant in project_saved_variants:
        saved_variants_by_project_family[saved_variant.project.guid][saved_variant.family.guid].append(saved_variant)

    return saved_variants_by_project_family


def generate_rows(project, loaded_samples_by_project_family, saved_variants_by_project_family, errors, update_omim_and_gene_symbols=True):
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
            "analysis_summary": (family.analysis_summary or '').strip('" \n'),
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

        submitted_to_mme = SEQR_ID_TO_MME_ID_MAP.find_one({'project_id': project.deprecated_project_id, 'family_id': family.family_id})
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
                "phenotype_class": "Known",
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

        saved_variants_to_json = {}
        for variant in saved_variants:
            if not variant.saved_variant_json:
                errors.append("%s - variant annotation not found" % variant)
                rows.append(row)
                continue

            saved_variant_json = json.loads(variant.saved_variant_json)

            annotation = saved_variant_json.get('annotation') or {}
            gene_ids = annotation.get("coding_gene_ids", [])
            if not gene_ids:
                gene_ids = annotation.get("gene_ids", [])

            if not gene_ids:
                errors.append("%s - no gene ids" % variant)
                rows.append(row)
                continue

            saved_variant_json['geneIds'] = gene_ids

            saved_variants_to_json[variant] = saved_variant_json

        affected_sample_ids = set()
        unaffected_sample_ids = set()
        for sample in samples:
            if sample.individual.affected == "A":
                affected_sample_ids.add(sample.sample_id)
            elif sample.individual.affected == "N":
                unaffected_sample_ids.add(sample.sample_id)

        potential_compound_het_genes = defaultdict(set)
        for variant, saved_variant_json in saved_variants_to_json.items():
            inheritance_models = set()

            affected_indivs_with_hom_alt_variants = set()
            affected_indivs_with_het_variants = set()
            unaffected_indivs_with_hom_alt_variants = set()
            unaffected_indivs_with_het_variants = set()
            is_x_linked = False

            genotypes = saved_variant_json.get('genotypes')
            if genotypes:
                chrom, _ = get_chrom_pos(variant.xpos_start)
                is_x_linked = "X" in chrom
                for sample_id, genotype in genotypes.items():
                    if genotype["num_alt"] == 2 and sample_id in affected_sample_ids:
                        affected_indivs_with_hom_alt_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 1 and sample_id in affected_sample_ids:
                        affected_indivs_with_het_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 2 and sample_id in unaffected_sample_ids:
                        unaffected_indivs_with_hom_alt_variants.add(i.individual_id)
                    elif genotype["num_alt"] == 1 and sample_id in unaffected_sample_ids:
                        unaffected_indivs_with_het_variants.add(i.individual_id)

            # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
            if not unaffected_indivs_with_hom_alt_variants and affected_indivs_with_hom_alt_variants:
                if is_x_linked:
                    inheritance_models.add("X-linked")
                else:
                    inheritance_models.add("AR-homozygote")

            if not unaffected_indivs_with_hom_alt_variants and not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
                if unaffected_sample_ids:
                    inheritance_models.add("de novo")
                else:
                    inheritance_models.add("AD")

            if not unaffected_indivs_with_hom_alt_variants and (len(
                    unaffected_sample_ids) < 2 or unaffected_indivs_with_het_variants) and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants:
                for gene_id in saved_variant_json['geneIds']:
                    potential_compound_het_genes[gene_id].add(variant)

            saved_variant_json['inheritance'] = inheritance_models

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
                        variant_main_transcript(saved_variants_to_json[variant])['geneId'] for variant in variants
                    }
                    if gene_id in main_gene_ids:
                        gene_ids_to_saved_variants[gene_id] = gene_ids_to_saved_variants[existing_gene_id]
                        del gene_ids_to_saved_variants[existing_gene_id]
                        gene_ids_to_variant_tag_names[gene_id] = gene_ids_to_variant_tag_names[existing_gene_id]
                        del gene_ids_to_variant_tag_names[existing_gene_id]
                else:
                    for variant in variants:
                        saved_variants_to_json[variant]['inheritance'] = {"AR-comphet"}
                        gene_ids_to_variant_tag_names[gene_id].update(
                            {vt.variant_tag_type.name for vt in variant.discovery_tags})
                    gene_ids_to_saved_variants[gene_id].update(variants)

        # Non-compound het variants are reported in the main transcript gene
        for variant, saved_variant_json in saved_variants_to_json.items():
            if "AR-comphet" not in saved_variant_json['inheritance']:
                gene_id = variant_main_transcript(saved_variant_json)['geneId']
                gene_ids_to_saved_variants[gene_id].add(variant)
                gene_ids_to_variant_tag_names[gene_id].update({vt.variant_tag_type.name for vt in variant.discovery_tags})
                gene_ids_to_inheritance[gene_id].update(saved_variant_json['inheritance'])

        if len(gene_ids_to_saved_variants) > 1:
            row["gene_count"] = len(gene_ids_to_saved_variants)

        for gene_id, variants in gene_ids_to_saved_variants.items():
            # create a copy of the row dict
            row = dict(row)

            row["actual_inheritance_model"] = ", ".join(gene_ids_to_inheritance[gene_id])

            row["gene_id"] = gene_id

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

            if any(tag in variant_tag_names for tag in [
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
                for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
                    if functional_field == ADDITIONAL_KINDREDS_FIELD:
                        row[functional_field] = "1"
                    elif functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                        row[functional_field] = "NA"
                    else:
                        row[functional_field] = "N"
            elif has_known_gene_for_phenotype:
                for functional_field in FUNCTIONAL_DATA_FIELD_MAP.values():
                    row[functional_field] = "KPG"

            variant_tag_list = []
            for variant in variants:
                variant_id = "-".join(map(str, list(get_chrom_pos(variant.xpos_start)) + [variant.ref, variant.alt]))
                variant_tag_list += [(variant_id, gene_id, vt.variant_tag_type.name.lower())
                                     for vt in variant.discovery_tags]

                for f in variant.variantfunctionaldata_set.all():
                    functional_field = FUNCTIONAL_DATA_FIELD_MAP[f.functional_data_tag]
                    if functional_field in METADATA_FUNCTIONAL_DATA_FIELDS:
                        value = f.metadata
                        if functional_field == ADDITIONAL_KINDREDS_FIELD:
                            value = str(int(value) + 1)
                        elif row[functional_field] != 'NS':
                            value = '{} {}'.format(row[functional_field], value)
                    else:
                        value = 'Y'

                    row[functional_field] = value

            row["extras_variant_tag_list"] = variant_tag_list

            rows.append(row)

    if update_omim_and_gene_symbols:
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
    omim_numbers = {row['omim_number_initial'] for row in rows if row['omim_number_initial']}
    omim_number_map = {}
    # OMIM API works for doing this as a single bulk request in theory but they detect us as a craweler and block us
    for omim_number_initial in omim_numbers:
        try:
            response = requests.get('https://www.omim.org/entry/' + omim_number_initial, headers={
                'Host': 'www.omim.org',
                'Connection': 'keep-alive',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            })

            if not response.ok:
                raise ValueError("omim request failed: %s %s" % (response, response.reason))
            omim_page_html = response.content

            # <a href="/phenotypicSeries/PS613280" class="btn btn-info" role="button"> Phenotypic Series </a>
            match = re.search("/phenotypicSeries/([a-zA-Z0-9]+)", omim_page_html)
            if not match:
                logger.debug("No phenotypic series found for OMIM initial # %s" % omim_number_initial)
            else:
                phenotypic_series_id = match.group(1)
                logger.debug("Will replace OMIM initial # %s with phenotypic series %s" % (omim_number_initial, phenotypic_series_id))
                omim_number_map[omim_number_initial] = phenotypic_series_id
        except Exception as e:
            # don't change omim_number_initial
            logger.info(
                "Unable to look up phenotypic series for OMIM initial number: %s. %s" % (omim_number_initial, e))

    for row in rows:
        if omim_number_map.get(row['omim_number_initial']):
            row['omim_number_initial'] = omim_number_map[row['omim_number_initial']]
