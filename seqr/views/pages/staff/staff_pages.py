from collections import defaultdict
import json
import logging
from pprint import pprint

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


ALL_PROJECTS = {
    "<label>": ["<project id>"],
    "<label2>": ["<project id1", "<project id2>"],
}


HEADER = [
    "T0",
    "Months since T0",
    "Family ID",
    "Phenotype",
    "Sequencing Approach",
    "Sample Source",
    "Analysis Status",
    "Expected Inheritance Model",
    "Actual Inheritance Model",
    "# Kindreds",
    "Gene Name",
    "Novel Mendelian Gene",
    "Gene Count",
    "Phenotype Class",
    "Solved",
    "Genome-wide Linkage",
    "Bonferroni corrected p-value, NA, NS, KPG",
    "# Kindreds w/ Overlapping SV & Similar Phenotype",
    "# Unrelated Kindreds w/ Causal Variants in Gene",
    "Biochemical Function",
    "Protein Interaction",
    "Expression",
    "Patient cells",
    "Non-patient cells",
    "Animal model",
    "Non-human Cell culture model",
    "Rescue",
    "OMIM # (initial)",
    "OMIM # (post-discovery)",
    "Abnormality of Connective Tissue",
    "Abnormality of the Voice",
    "Abnormality of the Nervous System",
    "Abnormality of the Breast",
    "Abnormality of the Eye",
    "Abnormality of Prenatal Development or Birth",
    "Neoplasm",
    "Abnormality of the Endocrine System",
    "Abnormality of Head or Neck",
    "Abnormality of the Immune System",
    "Growth Abnormality",
    "Abnormality of Limbs",
    "Abnormality of the Thoracic Cavity",
    "Abnormality of Blood and Blood-forming Tissues",
    "Abnormality of the Musculature",
    "Abnormality of the Cardiovascular System",
    "Abnormality of the Abdomen",
    "Abnormality of the Skeletal System",
    "Abnormality of the Respiratory System",
    "Abnormality of the Ear",
    "Abnormality of Metabolism / Homeostasis",
    "Abnormality of the Genitourinary System",
    "Abnormality of the Integument",
    "Submitted to MME (deadline 7 months post T0)",
    "Posted publicly (deadline 12 months posted T0)",
    "PubMed IDs for gene",
    "Collaborator",
    "Analysis Summary",
]

@staff_member_required
def discovery_sheet(request, project_guid=None):

    projects = [_get_json_for_project(project) for project in Project.objects.filter(name__icontains="cmg")]
    projects.sort(key=lambda project: project["name"])

    rows = []
    errors = []

    try:
        project = Project.objects.get(guid=project_guid)
    except ObjectDoesNotExist:
        return render(request, "staff/discovery_sheet.html", {
            'projects': projects,
            'rows': rows,
            'errors': errors,
        })

    loaded_datasets = list(Dataset.objects.filter(project=project, is_loaded=True))
    if not loaded_datasets:
        errors.append("No data loaded for project: %s" % project)
        logger.info("No data loaded for project: %s" % project)

        return render(request, "staff/discovery_sheet.html", {
            'projects': projects,
            'project': project,
            'rows': rows,
            'errors': errors,
        })

    t0 = max([dataset.loaded_date for dataset in loaded_datasets])

    t0_diff = rdelta.relativedelta(timezone.now(), t0)
    t0_months_since_t0 = t0_diff.years*12 + t0_diff.months

    for family in Family.objects.filter(project=project):
        individuals = list(Individual.objects.filter(family=family))
        samples = list(Sample.objects.filter(individual__family=family))
        sequencing_approach = ", ".join(set([sample.sample_type for sample in samples]))

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in individuals if i.phenotips_data]
        
        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_expected_inheritance_model = [
            inheritance_mode["label"] for phenotips_data in phenotips_individual_data_records for inheritance_mode in phenotips_data.get("global_mode_of_inheritance", [])
        ]
        omim_number_initial = ", ".join([disorder.get("id") for disorder in phenotips_individual_mim_disorders if "id" in disorder])

        analysis_complete_status = "first_pass_in_progress"
        if t0_months_since_t0 >= 12:
            analysis_complete_status = "complete"

        submitted_to_mme = any([individual.mme_submitted_data for individual in individuals if individual.mme_submitted_data])
            
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
            "analysis_complete_status": analysis_complete_status,  # If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project, or 1 year past t0 = complete.  If less than a year and none of the tags above = first pass in progress
            "expected_inheritance_model": ", ".join(set(phenotips_individual_expected_inheritance_model)) if phenotips_individual_expected_inheritance_model else "multiple", # example: 20161205_044436_852786_MAN_0851_05_1 -  AR-homozygote, AR, AD, de novo, X-linked, UPD, other, multiple  - phenotips - Global mode of inheritance:
            "omim_number_initial": omim_number_initial,
            "omim_number_post_discovery": family.post_discovery_omim_number or "",
            "collaborator": project.name,  # TODO use email addresses?
            "analysis_summary": family.analysis_summary.strip('" \n'),
            "phenotype_class": "Known" if omim_number_initial else "New",  # "disorders"  UE, NEW, MULTI, EXPAN, KNOWN - If there is a MIM number enter "Known" - otherwise put "New"  and then we will need to edit manually for the other possible values
            "solved": "",  # TIER 1 GENE (or known gene for phenotype also record as TIER 1 GENE), TIER 2 GENE, N - Pull from seqr using tags                
        }

        #for hpo_category_id, hpo_category_name in HPO_CATEGORY_NAMES.items():
        #    row[hpo_category_name.lower().replace(" ", "_").replace("/", "_")] = "N"
            
        for hpo_category_name in HPO_CATEGORY_NAMES:
            key = hpo_category_name.lower().replace(" ", "_").replace("/", "_")
            row[key] = "N"

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
                    logger.info("setting %s to Y" % key)
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
            
            variant_tag_type_names = [vt.variant_tag_type.name.lower() for vt in variant_tags]
            has_tier1 = any(name.startswith("tier 1") for name in variant_tag_type_names)
            has_tier2 = any(name.startswith("tier 2") for name in variant_tag_type_names)
            has_known_gene_for_phenotype = any(name == "known gene for phenotype" for name in variant_tag_type_names)

            chrom, pos = genomeloc.get_chr_pos(vt.xpos_start)
            variant_tag_list = ["%s-%s-%s-%s  %s  %s" % (chrom, pos, vt.ref, vt.alt, gene_symbol, vt.variant_tag_type.name.lower()) for vt in variant_tags]
            
            analysis_complete_status = "first_pass_in_progress"
            if t0_months_since_t0 >= 12 or has_tier1 or has_tier2 or has_known_gene_for_phenotype: 
                analysis_complete_status = "complete"

            row.update({
                "extras_variant_tag_list": variant_tag_list,
                "extras_num_variant_tags": len(variant_tags),

                "analysis_complete_status": analysis_complete_status,
                "gene_name": str(gene_symbol) if gene_symbol and (has_tier1 or has_tier2 or has_known_gene_for_phenotype) else "NS",
                "gene_count": len(gene_ids_to_variant_tags.keys()),
                "novel_mendelian_gene": "Y" if any("novel gene" in name for name in variant_tag_type_names) else "N",
            })
            
            rows.append(row)

    if request.GET.get("download"):
        export_table("discovery_sheet", HEADER, rows, file_format="xls")


    return render(request, "staff/discovery_sheet.html", {
        'project': project,
        'projects': projects,
        'header': HEADER,
        'rows': rows,
        'errors': errors,
    })

