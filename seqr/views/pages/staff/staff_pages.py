from collections import defaultdict
import json
import logging
import collections
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
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render
from settings import PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD
from seqr.views.utils.orm_to_json_utils import _get_json_for_project

logger = logging.getLogger(__name__)


@staff_member_required
def staff_dashboard(request):

    return render(request, "staff/staff_dashboard.html")


@staff_member_required
def users_page(request):

    return render(request, "staff/users_table.html", {
        'users': User.objects.all().order_by('email')
    })


HEADER = collections.OrderedDict([
    ("t0", "T0"),
    ("months_since_t0", "Months since T0"),
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
    ("submitted_to_mme", "Submitted to MME (deadline 7 months post T0)"),
    ("posted_publicly", "Posted publicly (deadline 12 months posted T0)"),
    ("pubmed_ids", "PubMed IDs for gene"),
    ("collaborator", "Collaborator"),
    ("analysis_summary", "Analysis Summary"),
])


PHENOTYPIC_SERIES_CACHE = {}

@staff_member_required
def discovery_sheet(request, project_guid=None):
    projects = [project for project in Project.objects.filter(name__icontains="cmg")]
    
    projects_json = []
    for project in Project.objects.filter(name__icontains="cmg"):
        if project.guid in PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD or \
            project.deprecated_project_id in PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD:
            continue

        projects_json.append( _get_json_for_project(project) )

    projects_json.sort(key=lambda project: project["name"])

    rows = []
    errors = []

    # export table for all cmg projects
    if "download" in request.GET and project_guid is None:
        logger.info("exporting xls table for all projects")
        for project in projects:
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

    for d in loaded_datasets:
        print("Loaded time %s: %s" % (d, d.loaded_date))
        
    #project_variant_tag_filter = Q(family__project=project) & (
    #            Q(variant_tag_type__name__icontains="tier 1") |
    #            Q(variant_tag_type__name__icontains="tier 2") |
    #            Q(variant_tag_type__name__icontains="known gene for phenotype"))

    #project_variant_tags = list(VariantTag.objects.select_related('variant_tag_type').filter(project_variant_tag_filter))
    #project_variant_tag_names = [vt.variant_tag_type.name.lower() for vt in project_variant_tags]
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
    for family in Family.objects.filter(project=project):
        individuals = list(Individual.objects.filter(family=family))
        samples = list(Sample.objects.filter(individual__family=family))

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in individuals if i.phenotips_data]
        
        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_expected_inheritance_model = [
            inheritance_mode["label"] for phenotips_data in phenotips_individual_data_records for inheritance_mode in phenotips_data.get("global_mode_of_inheritance", [])
        ]

        omim_ids = [disorder.get("id") for disorders in phenotips_individual_mim_disorders for disorder in disorders if "id" in disorder]
        omim_number_initial = omim_ids[0].replace("MIM:", "") if omim_ids else ""

        if omim_number_initial:
            if omim_number_initial not in PHENOTYPIC_SERIES_CACHE:
                try:
                    omim_page_html = requests.get('https://www.omim.org/entry/'+omim_number_initial)
                    # <a href="/phenotypicSeries/PS613280" class="btn btn-info" role="button"> Phenotypic Series </a>
                    match = re.search("/phenotypicSeries/([a-zA-Z0-9]+)", omim_page_html)
                    phenotypic_series_id = match.group(1)
                    logger.info("Will replace OMIM initial # %s with phenotypic series %s" % (omim_number_initial, phenotypic_series_id))
                    PHENOTYPIC_SERIES_CACHE[omim_number_initial] = phenotypic_series_id
                except Exception as e:
                    # don't change omim_number_initial
                    logger.info("Unable to look up phenotypic series for OMIM initial number: %s. %s" % (omim_number_initial, e))
                else:
                    omim_number_initial = PHENOTYPIC_SERIES_CACHE[omim_number_initial]
            else:
                omim_number_initial = PHENOTYPIC_SERIES_CACHE[omim_number_initial]


        submitted_to_mme = any([individual.mme_submitted_data for individual in individuals if individual.mme_submitted_data])

        #samples
        #print([s for s in samples])
        #print([(dataset, dataset.is_loaded, dataset.loaded_date) for sample in samples for dataset in sample.dataset_set.all()])

        datesets_loaded_date_for_family = [dataset.loaded_date for sample in samples for dataset in sample.dataset_set.filter(analysis_type="VARIANTS") if dataset.loaded_date is not None]
        if not datesets_loaded_date_for_family:
            errors.append("No data loaded for family: %s. Skipping..." % family)
            continue
        
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
        
        variant_tag_filter = Q(family=family) & (
            Q(variant_tag_type__name__icontains="tier 1") |
            Q(variant_tag_type__name__icontains="tier 2") |
            Q(variant_tag_type__name__icontains="known gene for phenotype"))

        variant_tags = list(VariantTag.objects.select_related('variant_tag_type').filter(variant_tag_filter))
        if not variant_tags:
            rows.append(row)
            continue

        gene_ids_to_variant_tags = defaultdict(list)
        for vt in variant_tags:
                  
            if not vt.variant_annotation:
                errors.append("%s - variant annotation not found" % vt)
                rows.append(row)
                continue

            vt.variant_annotation_json = json.loads(vt.variant_annotation)
            vt.variant_genotypes_json = json.loads(vt.variant_genotypes)
            
            if "coding_gene_ids" not in vt.variant_annotation_json and "gene_ids" not in vt.variant_annotation_json:
                errors.append("%s - no gene_ids" % vt)
                rows.append(row)
                continue

            gene_ids = vt.variant_annotation_json.get("coding_gene_ids", [])
            if not gene_ids:
                gene_ids = vt.variant_annotation_json.get("gene_ids", [])            
            if not gene_ids:
                errors.append("%s - gene_ids not specified" % vt)
                rows.append(row)
                continue
                
            for gene_id in gene_ids:
                gene_ids_to_variant_tags[gene_id].append(vt)

        for gene_id, variant_tags in gene_ids_to_variant_tags.items():
            gene_symbol = get_reference().get_gene_symbol(gene_id)
            
            lower_case_variant_tag_type_names = [vt.variant_tag_type.name.lower() for vt in variant_tags]
            has_tier1 = any(name.startswith("tier 1") for name in lower_case_variant_tag_type_names)
            has_tier2 = any(name.startswith("tier 2") for name in lower_case_variant_tag_type_names)
            has_known_gene_for_phenotype = any(name == "known gene for phenotype" for name in lower_case_variant_tag_type_names)

            has_tier1_phenotype_expansion = any(
                name.startswith("tier 1") and 'expansion' in name.lower() for name in lower_case_variant_tag_type_names)

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
                if vt.variant_genotypes:
                    chrom, pos = genomeloc.get_chr_pos(vt.xpos_start)
                    is_x_linked = "X" in chrom
                    for indiv_id, genotype in json.loads(vt.variant_genotypes).items():
                        i = Individual.objects.get(family=family, individual_id=indiv_id)
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
                    if is_x_linked:
                        actual_inheritance_models.add("X-linked")
                    else:
                        actual_inheritance_models.add("AR-homozygote")
                        
                if not unaffected_indivs_with_hom_alt_variants and not unaffected_indivs_with_het_variants and affected_indivs_with_het_variants:
                    if unaffected_total_individuals > 0:
                        actual_inheritance_models.add("de novo")
                    else:
                        actual_inheritance_models.add("AD")
                if not unaffected_indivs_with_hom_alt_variants and (unaffected_total_individuals < 2 or unaffected_indivs_with_het_variants) and affected_indivs_with_het_variants and not affected_indivs_with_hom_alt_variants:
                    potential_compound_hets[gene_id] += 1
                    print("%s incremented compound het for %s to %s" % (vt, gene_id, potential_compound_hets[gene_id]))
                    if potential_compound_hets[gene_id] >= 2:
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
            blank_or_KPG_or_NS = "" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else "NS")

            # "disorders"  UE, NEW, MULTI, EXPAN, KNOWN - If there is a MIM number enter "Known" - otherwise put "New"  and then we will need to edit manually for the other possible values
            phenotype_class = "EXPAN" if has_tier1_phenotype_expansion else ("KNOWN" if omim_number_initial else "NEW")

            row.update({
                "extras_variant_tag_list": variant_tag_list,
                "extras_num_variant_tags": len(variant_tags),
                "gene_name": str(gene_symbol) if gene_symbol and (has_tier1 or has_tier2 or has_known_gene_for_phenotype) else "NS",
                "gene_count": len(gene_ids_to_variant_tags.keys()) if len(gene_ids_to_variant_tags.keys()) > 1 else "NA",
                "novel_mendelian_gene": "Y" if any("novel gene" in name for name in lower_case_variant_tag_type_names) else ("N" if has_tier1 or has_tier2 or has_known_gene_for_phenotype else "NS"),
                "solved": ("TIER 1 GENE" if (has_tier1 or has_known_gene_for_phenotype) else ("TIER 2 GENE" if has_tier2 else "N")),
                "posted_publicly": ("" if has_tier1 or has_tier2 or has_known_gene_for_phenotype else "NS"),
                "submitted_to_mme": "TBD" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else ("Y" if submitted_to_mme else "NS")),
                "actual_inheritance_model": actual_inheritance_model,
                "analysis_complete_status": analysis_complete_status,  # If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project, or 1 year past t0 = complete.  If less than a year and none of the tags above = first pass in progress
                "genome_wide_linkage": NA_or_KPG_or_NS,
                "p_value": NA_or_KPG_or_NS,
                "n_kindreds_overlapping_sv_similar_phenotype": NA_or_KPG_or_NS,
                "n_unrelated_kindreds_with_causal_variants_in_gene": "1" if has_tier1 or has_tier2 else ("KPG" if has_known_gene_for_phenotype else "NS"),
                "biochemical_function": blank_or_KPG_or_NS,
                "protein_interaction": blank_or_KPG_or_NS,
                "expression": blank_or_KPG_or_NS,
                "patient_cells": blank_or_KPG_or_NS,
                "non_patient_cell_model": blank_or_KPG_or_NS,
                "animal_model": blank_or_KPG_or_NS,
                "non_human_cell_culture_model": blank_or_KPG_or_NS,
                "rescue": blank_or_KPG_or_NS,
                "phenotype_class": phenotype_class,
            })
            
            rows.append(row)

    return rows
