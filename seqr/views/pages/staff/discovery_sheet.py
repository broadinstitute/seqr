from collections import defaultdict
import collections
import json
import logging
import re
import requests

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from seqr.views.utils.export_table_utils import export_table
from xbrowse_server.mall import get_reference
from xbrowse import genomeloc
from reference_data.models import HPO_CATEGORY_NAMES
from seqr.models import Project, Family, Sample, Dataset, Individual, VariantTag
from dateutil import relativedelta as rdelta
from django.db.models import Q
from django.shortcuts import render
from settings import PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD, LOGIN_URL
from seqr.views.utils.orm_to_json_utils import _get_json_for_project

logger = logging.getLogger(__name__)



HEADER = collections.OrderedDict([
    ("t0", "T0"),
    ("family_id", "Family ID"),
    ("coded_phenotype", "Phenotype"),
    ("sequencing_approach", "Sequencing Approach"),
    ("sample_source", "Sample Source"),
    ("analysis_complete_status", "Analysis Status"),
    ("expected_inheritance_model", "Expected Inheritance Model"),
    ("actual_inheritance_model", "Actual Inheritance Model"),
    ("n_kindreds", "# Kindreds"),
    ("gene_name", "Gene Name"),
    ("novel_mendelian_gene", "Novel Mendelian Gene"),
    ("gene_count", "Gene Count"),
    ("phenotype_class", "Phenotype Class"),
    ("solved", "Solved"),
    ("genome_wide_linkage", "Genome-wide Linkage"),
    ("p_value", "Bonferroni corrected p-value, NA, NS, KPG"),
    ("n_kindreds_overlapping_sv_similar_phenotype", "# Kindreds w/ Overlapping SV & Similar Phenotype"),
    ("n_unrelated_kindreds_with_causal_variants_in_gene", "# Unrelated Kindreds w/ Causal Variants in Gene"),
    ("biochemical_function", "Biochemical Function"),
    ("protein_interaction", "Protein Interaction"),
    ("expression", "Expression"),
    ("patient_cells", "Patient cells"),
    ("non_patient_cell_model", "Non-patient cells"),
    ("animal_model", "Animal model"),
    ("non_human_cell_culture_model", "Non-human Cell culture model"),
    ("rescue", "Rescue"),
    ("omim_number_initial", "OMIM # (initial)"),
    ("omim_number_post_discovery", "OMIM # (post-discovery)"),
    ("connective_tissue", "Abnormality of Connective Tissue"),
    ("voice", "Abnormality of the Voice"),
    ("nervous_system", "Abnormality of the Nervous System"),
    ("breast", "Abnormality of the Breast"),
    ("eye_defects", "Abnormality of the Eye"),
    ("prenatal_development_or_birth", "Abnormality of Prenatal Development or Birth"),
    ("neoplasm", "Neoplasm"),
    ("endocrine_system", "Abnormality of the Endocrine System"),
    ("head_or_neck", "Abnormality of Head or Neck"),
    ("immune_system", "Abnormality of the Immune System"),
    ("growth", "Growth Abnormality"),
    ("limbs", "Abnormality of Limbs"),
    ("thoracic_cavity", "Abnormality of the Thoracic Cavity"),
    ("blood", "Abnormality of Blood and Blood-forming Tissues"),
    ("musculature", "Abnormality of the Musculature"),
    ("cardiovascular_system", "Abnormality of the Cardiovascular System"),
    ("abdomen", "Abnormality of the Abdomen"),
    ("skeletal_system", "Abnormality of the Skeletal System"),
    ("respiratory", "Abnormality of the Respiratory System"),
    ("ear_defects", "Abnormality of the Ear"),
    ("metabolism_homeostasis", "Abnormality of Metabolism / Homeostasis"),
    ("genitourinary_system", "Abnormality of the Genitourinary System"),
    ("integument", "Abnormality of the Integument"),
    ("t0_copy", "T0"),
    ("months_since_t0", "Months since T0"),
    ("submitted_to_mme", "Submitted to MME (deadline 7 months post T0)"),
    ("posted_publicly", "Posted publicly (deadline 12 months posted T0)"),
    ("komp_early_release", "KOMP Early Release"),
    ("pubmed_ids", "PubMed IDs for gene"),
    ("collaborator", "Collaborator"),
    ("analysis_summary", "Analysis Summary"),
])


PHENOTYPIC_SERIES_CACHE = {}

@staff_member_required(login_url=LOGIN_URL)
def discovery_sheet(request, project_guid=None):
    projects = Project.objects.filter(projectcategory__name__iexact='cmg').distinct()

    projects_json = [_get_json_for_project(project, request.user, add_project_category_guids_field=False) for project in projects]
    projects_json.sort(key=lambda project: project["name"])

    rows = []
    errors = []

    # export table for all cmg projects
    if "download" in request.GET and project_guid is None:
        logger.info("exporting xls table for all projects")
        for project in projects:
            if any([proj_id.lower() == exclude_id.lower()
                    for exclude_id in PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD
                    for proj_id in [project.guid, project.deprecated_project_id]]):
                continue

            rows.extend(
                generate_rows(project, errors)
            )

        return export_table("discovery_sheet", HEADER, rows, file_format="xls")

    # generate table for 1 project
    try:
        project = Project.objects.get(guid=project_guid)
    except ObjectDoesNotExist:
        return render(request, "staff/discovery_sheet.html", {
            'projects': projects_json,
            'rows': rows,
            'errors': errors,
        })

    rows = generate_rows(project, errors)

    logger.info("request.get: " + str(request.GET))
    if "download" in request.GET:
        logger.info("exporting xls table")
        return export_table("discovery_sheet", HEADER, rows, file_format="xls")

    return render(request, "staff/discovery_sheet.html", {
        'project': project,
        'projects': projects_json,
        'header': HEADER.values(),
        'rows': rows,
        'errors': errors,
    })


def generate_rows(project, errors):
    rows = []

    loaded_datasets = list(Dataset.objects.filter(project=project, analysis_type="VARIANTS", is_loaded=True))
    if not loaded_datasets:
        errors.append("No data loaded for project: %s" % project)
        logger.info("No data loaded for project: %s" % project)
        return []

    loaded_datasets_by_family = collections.defaultdict(set)
    for d in loaded_datasets:
        print("Loaded time %s: %s" % (d, d.loaded_date))
        for sample in d.samples.select_related('individual__family').all():
            loaded_datasets_by_family[sample.individual.family.guid].add(d)

    project_variant_tag_filter = Q(family__project=project) & (
               Q(variant_tag_type__name__icontains="tier 1") |
               Q(variant_tag_type__name__icontains="tier 2") |
               Q(variant_tag_type__name__icontains="known gene for phenotype"))

    project_variant_tags = list(VariantTag.objects.select_related('variant_tag_type').select_related('family').select_related('family__project').filter(project_variant_tag_filter))
    # project_variant_tag_names = [vt.variant_tag_type.name.lower() for vt in project_variant_tags]
    #project_has_tier1 = any([vt_name.startswith("tier 1") for vt_name in project_variant_tag_names])
    #project_has_tier2 = any([vt_name.startswith("tier 2") for vt_name in project_variant_tag_names])
    #project_has_known_gene_for_phenotype = any([(vt_name == "known gene for phenotype") for vt_name in project_variant_tag_names])


    #"External" = REAN
    #"RNA" = RNA
    #"WGS" or "Genome" . = WGS
    #else  "WES"
    lower_case_project_id = project.deprecated_project_id.lower()
    if "external" in lower_case_project_id or "reprocessed" in lower_case_project_id:
        sequencing_approach = "REAN"
    elif "rna" in lower_case_project_id:
        sequencing_approach = "RNA"
    elif "wgs" in lower_case_project_id or "genome" in lower_case_project_id:
        sequencing_approach = "WGS"
    else:
        sequencing_approach = "WES"

    now = timezone.now()
    for family in Family.objects.filter(project=project).prefetch_related('individual_set'):
        datesets_loaded_date_for_family = [dataset.loaded_date for dataset in loaded_datasets_by_family[family.guid] if
                                           dataset.loaded_date is not None]
        if not datesets_loaded_date_for_family:
            errors.append("No data loaded for family: %s. Skipping..." % family)
            continue

        individuals = list(family.individual_set.all())

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in individuals if i.phenotips_data]

        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_expected_inheritance_model = [
            inheritance_mode["label"] for phenotips_data in phenotips_individual_data_records for inheritance_mode in phenotips_data.get("global_mode_of_inheritance", [])
        ]

        omim_ids = [disorder.get("id") for disorders in phenotips_individual_mim_disorders for disorder in disorders if "id" in disorder]
        omim_number_initial = omim_ids[0].replace("MIM:", "") if omim_ids else ""

        if omim_number_initial:
            if omim_number_initial in PHENOTYPIC_SERIES_CACHE:
                omim_number_initial = PHENOTYPIC_SERIES_CACHE[omim_number_initial]
            else:
                try:
                    response = requests.get('https://www.omim.org/entry/'+omim_number_initial, headers={
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
                        logger.info("No phenotypic series found for OMIM initial # %s" % omim_number_initial)
                        PHENOTYPIC_SERIES_CACHE[omim_number_initial] = omim_number_initial
                    else:
                        phenotypic_series_id = match.group(1)
                        logger.info("Will replace OMIM initial # %s with phenotypic series %s" % (omim_number_initial, phenotypic_series_id))
                        PHENOTYPIC_SERIES_CACHE[omim_number_initial] = phenotypic_series_id
                        omim_number_initial = PHENOTYPIC_SERIES_CACHE[omim_number_initial]
                except Exception as e:
                    # don't change omim_number_initial
                    logger.info("Unable to look up phenotypic series for OMIM initial number: %s. %s" % (omim_number_initial, e))

        submitted_to_mme = any([individual.mme_submitted_data for individual in individuals if individual.mme_submitted_data])

        t0 = min(datesets_loaded_date_for_family)

        t0_diff = rdelta.relativedelta(now, t0)
        t0_months_since_t0 = t0_diff.years*12 + t0_diff.months

        analysis_complete_status = "first_pass_in_progress"
        if t0_months_since_t0 >= 12: # or (project_has_tier1 or project_has_tier2 or project_has_known_gene_for_phenotype):
            analysis_complete_status = "complete"

        row = {
            "extras_pedigree_url": family.pedigree_image.url if family.pedigree_image else "",

            "project_id": project.deprecated_project_id,
            "project_name": project.name,
            "t0": t0,
            "months_since_t0": t0_months_since_t0,
            "family_id": family.family_id,
            "coded_phenotype": family.coded_phenotype or "",  # "Coded Phenotype" field - Ben will add a field that only staff can edit.  Will be on the family page, above short description.
            "sequencing_approach": sequencing_approach,  # WES, WGS, RNA, REAN, GENO - Ben will do this using a script based off project name - may need to backfill some
            "sample_source": "CMG",  # CMG, NHLBI-X01, NHLBI-nonX01, NEI - Most are CMG so default to them all being CMG.
            "n_kindreds": "1",
            "actual_inheritance_model": "",
            "expected_inheritance_model": "".join(set(phenotips_individual_expected_inheritance_model)) if len(set(phenotips_individual_expected_inheritance_model)) == 1 else "multiple", # example: 20161205_044436_852786_MAN_0851_05_1 -  AR-homozygote, AR, AD, de novo, X-linked, UPD, other, multiple  - phenotips - Global mode of inheritance:
            "omim_number_initial": omim_number_initial or "NA",
            "omim_number_post_discovery": family.post_discovery_omim_number or "NA",
            "collaborator": project.name,  # TODO use email addresses?
            "analysis_summary": family.analysis_summary.strip('" \n'),
            "phenotype_class": "Known" if omim_number_initial else "New",  # "disorders"  UE, NEW, MULTI, EXPAN, KNOWN - If there is a MIM number enter "Known" - otherwise put "New"  and then we will need to edit manually for the other possible values
            "solved": "N",  # TIER 1 GENE (or known gene for phenotype also record as TIER 1 GENE), TIER 2 GENE, N - Pull from seqr using tags
            "submitted_to_mme": "Y" if submitted_to_mme else "NS",
            "pubmed_ids": "",
            "posted_publicly": "NS",

            "gene_name": "NS",
            "gene_count": "NA",
            "novel_mendelian_gene": "NS",
            "analysis_complete_status": analysis_complete_status,  # If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project, or 1 year past t0 = complete.  If less than a year and none of the tags above = first pass in progress

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
        }

        #for hpo_category_id, hpo_category_name in HPO_CATEGORY_NAMES.items():
        #    row[hpo_category_name.lower().replace(" ", "_").replace("/", "_")] = "N"

        for hpo_category_name in [
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
        ]:
            row[hpo_category_name] = "N"

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

        variant_tags = [vt for vt in project_variant_tags if vt.family == family]
        if not variant_tags:
            rows.append(row)
            continue

        gene_ids_to_variant_tags = defaultdict(list)
        for vt in variant_tags:

            if not vt.saved_variant_json:
                errors.append("%s - variant annotation not found" % vt)
                rows.append(row)
                continue

            vt.saved_variant_json = json.loads(vt.saved_variant_json)

            if "coding_gene_ids" not in vt.saved_variant_json["annotation"] and "gene_ids" not in vt.saved_variant_json["annotation"]:
                errors.append("%s - no gene_ids" % vt)
                rows.append(row)
                continue

            gene_ids = vt.saved_variant_json["annotation"].get("coding_gene_ids", [])
            if not gene_ids:
                gene_ids = vt.saved_variant_json["annotation"].get("gene_ids", [])

            if not gene_ids:
                errors.append("%s - gene_ids not specified" % vt)
                rows.append(row)
                continue

            # get the shortest gene_id
            gene_id = list(sorted(gene_ids, key=lambda gene_id: len(gene_id)))[0]

            gene_ids_to_variant_tags[gene_id].append(vt)

        for gene_id, variant_tags in gene_ids_to_variant_tags.items():
            gene_symbol = get_reference().get_gene_symbol(gene_id)

            lower_case_variant_tag_type_names = [vt.variant_tag_type.name.lower() for vt in variant_tags]
            has_tier1 = any(name.startswith("tier 1") for name in lower_case_variant_tag_type_names)
            has_tier2 = any(name.startswith("tier 2") for name in lower_case_variant_tag_type_names)
            has_tier2_phenotype_expansion = any(name.startswith("tier 2") and "expansion" in name for name in lower_case_variant_tag_type_names)
            has_known_gene_for_phenotype = any(name == "known gene for phenotype" for name in lower_case_variant_tag_type_names)

            has_tier1_phenotype_expansion_or_novel_mode_of_inheritance = any(
                name.startswith("tier 1") and ('expansion' in name.lower() or 'novel mode' in name.lower()) for name in lower_case_variant_tag_type_names)
            has_tier_1_or_2_phenotype_not_delineated = any(
                (name.startswith("tier 1") or name.startswith("tier 2")) and ('not delineated' in name.lower()) for name in lower_case_variant_tag_type_names)

            analysis_complete_status = row["analysis_complete_status"]
            if has_tier1 or has_tier2 or has_known_gene_for_phenotype:
                analysis_complete_status = "complete"

            variant_tag_list = [("%s  %s  %s" % ("-".join(map(str, list(genomeloc.get_chr_pos(vt.xpos_start)) + [vt.ref, vt.alt])), gene_symbol, vt.variant_tag_type.name.lower())) for vt in variant_tags]

            actual_inheritance_models = set()
            potential_compound_hets = defaultdict(int)  # gene_id to compound_hets counter
            for vt in variant_tags:
                affected_indivs_with_hom_alt_variants = set()
                affected_indivs_with_het_variants = set()
                affected_total_individuals = 0
                unaffected_indivs_with_hom_alt_variants = set()
                unaffected_indivs_with_het_variants = set()
                unaffected_total_individuals = 0
                is_x_linked = False
                if vt.saved_variant_json["genotypes"]:
                    chrom, pos = genomeloc.get_chr_pos(vt.xpos_start)
                    is_x_linked = "X" in chrom
                    for indiv_id, genotype in vt.saved_variant_json["genotypes"].items():
                        try:
                            i = next(i for i in individuals if i.individual_id == indiv_id)
                        except StopIteration as e:
                            logger.warn("WARNING: Couldn't find individual: %s, %s" % (family, indiv_id))
                            continue

                        if i.affected == "A":
                            affected_total_individuals += 1
                        elif i.affected == "N":
                            unaffected_total_individuals += 1

                        if genotype["num_alt"] == 2 and i.affected == "A":
                            affected_indivs_with_hom_alt_variants.add(indiv_id)
                        elif genotype["num_alt"] == 1 and i.affected == "A":
                            affected_indivs_with_het_variants.add(indiv_id)
                        elif genotype["num_alt"] == 2 and i.affected == "N":
                            unaffected_indivs_with_hom_alt_variants.add(indiv_id)
                        elif genotype["num_alt"] == 1 and i.affected == "N":
                            unaffected_indivs_with_het_variants.add(indiv_id)

                # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple
                if not unaffected_indivs_with_hom_alt_variants and affected_indivs_with_hom_alt_variants:
                    if "AR-comphet" not in actual_inheritance_models:
                        if is_x_linked:
                            actual_inheritance_models.add("X-linked")
                        else:
                            actual_inheritance_models.add("AR-homozygote")

                if not unaffected_indivs_with_hom_alt_variants and not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
                    if "AR-comphet" not in actual_inheritance_models:
                        if unaffected_total_individuals > 0:
                            actual_inheritance_models.add("de novo")
                        else:
                            actual_inheritance_models.add("AD")

                if not unaffected_indivs_with_hom_alt_variants and (unaffected_total_individuals < 2 or unaffected_indivs_with_het_variants) and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants:
                    potential_compound_hets[gene_id] += 1
                    print("%s incremented compound het for %s to %s" % (vt, gene_id, potential_compound_hets[gene_id]))
                    if potential_compound_hets[gene_id] >= 2:
                        actual_inheritance_models.clear()
                        actual_inheritance_models.add("AR-comphet")

            actual_inheritance_model = " (%d aff hom, %d aff het, %d unaff hom, %d unaff het) " % (
                #affected_total_individuals,
                #unaffected_total_individuals,
                len(affected_indivs_with_hom_alt_variants),
                len(affected_indivs_with_het_variants),
                len(unaffected_indivs_with_hom_alt_variants),
                len(unaffected_indivs_with_het_variants),
            )

            actual_inheritance_model = ", ".join(actual_inheritance_models) #+ actual_inheritance_model
            NA_or_KPG_or_NS = "NA" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else "NS")
            KPG_or_blank_or_NS = "KPG" if has_known_gene_for_phenotype else ("" if has_tier1 or has_tier2 else "NS")

            # "disorders"  UE, NEW, MULTI, EXPAN, KNOWN - If there is a MIM number enter "Known" - otherwise put "New"  and then we will need to edit manually for the other possible values
            phenotype_class = "EXPAN" if has_tier1_phenotype_expansion_or_novel_mode_of_inheritance or has_tier2_phenotype_expansion else (
                "UE" if has_tier_1_or_2_phenotype_not_delineated else (
                    "Known" if omim_number_initial else "New"))

            # create a copy of the row dict
            row = dict(row)

            row.update({
                "extras_variant_tag_list": variant_tag_list,
                "extras_num_variant_tags": len(variant_tags),
                "gene_name": str(gene_symbol) if gene_symbol and (has_tier1 or has_tier2 or has_known_gene_for_phenotype) else "NS",
                "gene_count": len(gene_ids_to_variant_tags.keys()) if len(gene_ids_to_variant_tags.keys()) > 1 else "NA",
                "novel_mendelian_gene": "Y" if any("novel gene" in name for name in lower_case_variant_tag_type_names) else ("N" if has_tier1 or has_tier2 or has_known_gene_for_phenotype or has_tier2_phenotype_expansion else "NS"),
                "solved": ("TIER 1 GENE" if (has_tier1 or has_known_gene_for_phenotype) else ("TIER 2 GENE" if has_tier2 else "N")),
                "posted_publicly": ("" if has_tier1 or has_tier2 or has_known_gene_for_phenotype else "NS"),
                "submitted_to_mme": "Y" if submitted_to_mme else ("TBD" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else "NS")),
                "actual_inheritance_model": actual_inheritance_model,
                "analysis_complete_status": analysis_complete_status,  # If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project, or 1 year past t0 = complete.  If less than a year and none of the tags above = first pass in progress
                "genome_wide_linkage": NA_or_KPG_or_NS,
                "p_value": NA_or_KPG_or_NS,
                "n_kindreds_overlapping_sv_similar_phenotype": NA_or_KPG_or_NS,
                "n_unrelated_kindreds_with_causal_variants_in_gene": "1" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else "NS"),
                "biochemical_function": KPG_or_blank_or_NS,
                "protein_interaction": KPG_or_blank_or_NS,
                "expression": KPG_or_blank_or_NS,
                "patient_cells": KPG_or_blank_or_NS,
                "non_patient_cell_model": KPG_or_blank_or_NS,
                "animal_model": KPG_or_blank_or_NS,
                "non_human_cell_culture_model": KPG_or_blank_or_NS,
                "rescue": KPG_or_blank_or_NS,
                "phenotype_class": phenotype_class,
            })

            rows.append(row)

    return rows
