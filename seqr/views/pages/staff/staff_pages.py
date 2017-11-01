import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from reference_data.models import HPO_CATEGORY_NAMES
from seqr.models import Project, Family, Sample, Dataset, Individual, VariantTag
from dateutil import relativedelta as rdelta
from django.contrib.auth.models import User
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
        variant_tags = list(VariantTag.objects.select_related('variant_tag_type').filter(family=family))
        if not variant_tags:
            errors.append("No variant tags in family: %s. Skipping..." % family)
            logger.info("No variant tags in family: %s. Skipping... " % family)
            continue

        variant_tag_names = [vt.variant_tag_type.name for vt in variant_tags]

        gene_names = [variant_tag.variant_annotation for variant_tag in variant_tags]

        individuals = list(Individual.objects.filter(family=family))
        samples = list(Sample.objects.filter(individual__family=family))
        sequencing_approach = ", ".join(set([sample.sample_type for sample in samples]))

        submitted_to_mme = any([individual.mme_submitted_data for individual in individuals if individual.mme_submitted_data])

        phenotips_individual_data_records = [json.loads(i.phenotips_data) for i in individuals if i.phenotips_data]
        phenotips_individual_features = [phenotips_data.get("features", []) for phenotips_data in phenotips_individual_data_records]
        phenotips_individual_mim_disorders = [phenotips_data.get("disorders", []) for phenotips_data in phenotips_individual_data_records]
        omim_number_initial = ", ".join([disorder.get("id") for disorder in phenotips_individual_mim_disorders if "id" in disorder])
        row = {
            "project": project.name,
            "t0": t0,
            "months_since_t0": t0_months_since_t0,
            "family_id": family.family_id,
            "phenotype": "",  # "Coded Phenotype" field - Ben will add a field that only staff can edit.  Will be on the family page, above short description.
            "sequencing_approach": sequencing_approach,  # WES, WGS, RNA, REAN, GENO - Ben will do this using a script based off project name - may need to backfill some
            "sample_source": "CMG",  # CMG, NHLBI-X01, NHLBI-nonX01, NEI - Most are CMG so default to them all being CMG.
            "expected_inheritance_model": "", # example: 20161205_044436_852786_MAN_0851_05_1 -  AR-homozygote, AR, AD, de novo, X-linked, UPD, other, multiple  - phenotips - Global mode of inheritance:
            "gene_count": len(gene_names),
            "omim_number_initial": omim_number_initial,
            "omim_number_post_discovery": "",
            "submitted_to_mme": "Y" if submitted_to_mme else "N",
            "posted_publicly": "",
            "pubmed_ids": "",
            "collaborator": project.name,  # TODO use email addresses?
            "analysis_summary": family.analysis_summary.strip('" \n'),
        }


        #for hpo_category_id, hpo_category_name in HPO_CATEGORY_NAMES.items():
        #    row[hpo_category_name.lower().replace(" ", "_").replace("/", "_")] = "N"
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

        for gene_name in gene_names:
            analysis_status = "first_pass_in_progress"
            if t0_months_since_t0 >= 12:  # TODO add rest of conditions - tier 1 or tier or known gene for phenotype
                analysis_status = "complete"

            row_per_gene = dict(row)  # make a copy

            row_per_gene.update({
                "analysis_status": analysis_status,  # If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project, or 1 year past t0 = complete.  If less than a year and none of the tags above = first pass in progress
                "actual_inheritance_model": "", # AR-homozygote, AR-comphet, AR, AD, de novo, X-linked, UPD, other, multiple - If known gene for phenotype, tier 1 or tier 2 tag is used on any variant  in project a drop down would be enabled with the options listed in the cell to the right.  If multiple variants have different values the result would show up as "multiple"
                "gene_name": gene_name if gene_name else "",
                "novel_mendelian_gene": "",
                "phenotype_class": "",  # "disorders"  UE, NEW, MULTI, EXPAN, KNOWN - If there is a MIM number enter "Known" - otherwise put "New"  and then we will need to edit manually for the other possible values
                "solved": "",  # TIER 1 GENE (or known gene for phenotype also record as TIER 1 GENE), TIER 2 GENE, N - Pull from seqr using tags
            })

            # "disorders"

            rows.append(row_per_gene)

    return render(request, "staff/discovery_sheet.html", {
        'project': project,
        'projects': projects,
        'rows': rows,
        'errors': errors,
    })


"""
{"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005009", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "last_modification_date": "2016-05-27T11:56:56.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-05-27T04:06:17.774Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:24:57.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B354_11_A", "id": "P0005009", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005009"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005010", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "F", "last_modification_date": "2016-05-27T11:56:42.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-05-27T04:06:17.774Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:24:58.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B354_12_A", "id": "P0005010", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005010"}, {"features": [{"observed": "yes", "category": "HP:0000119", "type": "phenotype", "id": "HP:0001967", "label": "Diffuse mesangial sclerosis"}, {"observed": "yes", "category": "HP:0001626", "type": "phenotype", "id": "HP:0000822", "label": "Hypertension"}, {"observed": "no", "category": "HP:0000119", "type": "phenotype", "id": "HP:0000100", "label": "Nephrotic syndrome"}, {"observed": "yes", "category": "HP:0000119", "type": "phenotype", "id": "HP:0000093", "label": "Proteinuria"}], "links": {"href": "http://phenotips:8080/rest/patients/P0005011", "rel": "self"}, "nonstandard_features": [], "sex": "M", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-17T04:07:28.084Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:11:49.803Z", "score": 0.7486995933452297, "server": "local-omim"}, "last_modification_date": "2016-06-17T15:32:19.000Z", "id": "P0005011", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "family_history": {}, "date_of_birth": "", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "date": "2016-05-06T18:24:59.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0005011", "notes": {"indication_for_referral": "non-nephrotic range proteinuria with UPC 0.4-0.5, slightly elevated BP, no nephrotic syndrome, no biopsy"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "HIL_B354_21_A"}, {"features": [{"observed": "yes", "category": "HP:0000119", "type": "phenotype", "id": "HP:0001967", "label": "Diffuse mesangial sclerosis"}, {"category": "HP:0000119", "notes": "Post renal transplant", "label": "Stage 5 chronic kidney disease", "observed": "yes", "type": "phenotype", "id": "HP:0003774"}], "links": {"href": "http://phenotips:8080/rest/patients/P0005012", "rel": "self"}, "nonstandard_features": [], "sex": "M", "date": "2016-05-06T18:25:00.000Z", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-05-27T04:06:17.774Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:11:49.492Z", "score": 0.6498047849711148, "server": "local-omim"}, "last_modification_date": "2016-05-27T11:56:11.000Z", "id": "P0005012", "ethnicity": {"maternal_ethnicity": ["Arabs"], "paternal_ethnicity": ["Arabs"]}, "family_history": {"consanguinity": true}, "rejectedGenes": [{"gene": "95 gene \"carve out panel\" from whole exome sequencing", "comments": "negative for 95 known monogenic causes of pediatric kidney disease (including 36 monogenic causes of nephrotic syndrome) performed by hildebrandt lab"}], "date_of_birth": "", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "global_mode_of_inheritance": [{"id": "HP:0000007", "label": "Autosomal recessive inheritance"}], "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0005012", "global_age_of_onset": [{"id": "HP:0011463", "label": "Childhood onset"}], "notes": {"indication_for_referral": "Diffuse Mesangial Sclerosis"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "HIL_B354_22_A"}		N			CMG_Hildebrandt_Exomes
{"life_status": "alive", "links": {"href": "http://phenotips:8080/rest/patients/P0010235", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "F", "last_modification_date": "2016-11-14T16:00:28.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-14T05:46:50.364Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-11-14T16:00:26.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "external_id": "20161114_154653_722642_HIL_F983_12_1", "id": "P0010235", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0010235"}, {"features": [{"observed": "yes", "category": "HP:0000119", "type": "phenotype", "id": "HP:0012588", "label": "Steroid-resistant nephrotic syndrome"}], "links": {"href": "http://phenotips:8080/rest/patients/P0010233", "rel": "self"}, "nonstandard_features": [], "sex": "F", "date": "2016-11-14T16:00:23.000Z", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-28T05:42:24.616Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:13:32.870Z", "score": 0.5767262369077334, "server": "local-omim"}, "last_modification_date": "2016-11-28T16:24:33.000Z", "id": "P0010233", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "family_history": {"consanguinity": false}, "rejectedGenes": [{"gene": "nphs2", "comments": "Negative PCR-based testing\r\n"}], "date_of_birth": "2000-01-01", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "global_mode_of_inheritance": [{"id": "HP:0000007", "label": "Autosomal recessive inheritance"}], "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0010233", "global_age_of_onset": [{"id": "HP:0011463", "label": "Childhood onset"}], "notes": {"indication_for_referral": "Steroid Resistant Nephrotic Syndrome\r\n"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "20161114_154653_700314_HIL_F983_21_1"}, {"life_status": "alive", "report_id": "P0010234", "links": {"href": "http://localhost:8080/rest/patients/P0010234", "rel": "self"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modification_date": "2016-11-14T21:00:26.000Z", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "solved": {"status": "unsolved"}, "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-14T05:46:50.364Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "specificity": {"date": "2017-06-21T03:40:12.467Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-11-14T21:00:25.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "external_id": "20161114_154653_712323_HIL_F983_11_1", "id": "P0010234", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "prenatal_perinatal_history": {}}		N			CMG_Hildebrandt_Exomes
{"life_status": "alive", "links": {"href": "http://phenotips:8080/rest/patients/P0010235", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "F", "last_modification_date": "2016-11-14T16:00:28.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-14T05:46:50.364Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-11-14T16:00:26.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "external_id": "20161114_154653_722642_HIL_F983_12_1", "id": "P0010235", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0010235"}, {"features": [{"observed": "yes", "category": "HP:0000119", "type": "phenotype", "id": "HP:0012588", "label": "Steroid-resistant nephrotic syndrome"}], "links": {"href": "http://phenotips:8080/rest/patients/P0010233", "rel": "self"}, "nonstandard_features": [], "sex": "F", "date": "2016-11-14T16:00:23.000Z", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-28T05:42:24.616Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:13:32.870Z", "score": 0.5767262369077334, "server": "local-omim"}, "last_modification_date": "2016-11-28T16:24:33.000Z", "id": "P0010233", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "family_history": {"consanguinity": false}, "rejectedGenes": [{"gene": "nphs2", "comments": "Negative PCR-based testing\r\n"}], "date_of_birth": "2000-01-01", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "global_mode_of_inheritance": [{"id": "HP:0000007", "label": "Autosomal recessive inheritance"}], "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0010233", "global_age_of_onset": [{"id": "HP:0011463", "label": "Childhood onset"}], "notes": {"indication_for_referral": "Steroid Resistant Nephrotic Syndrome\r\n"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "20161114_154653_700314_HIL_F983_21_1"}, {"life_status": "alive", "report_id": "P0010234", "links": {"href": "http://localhost:8080/rest/patients/P0010234", "rel": "self"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modification_date": "2016-11-14T21:00:26.000Z", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "solved": {"status": "unsolved"}, "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-11-14T05:46:50.364Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "specificity": {"date": "2017-06-21T03:40:12.467Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-11-14T21:00:25.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "external_id": "20161114_154653_712323_HIL_F983_11_1", "id": "P0010234", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "prenatal_perinatal_history": {}}		N			CMG_Hildebrandt_Exomes
{"features": [{"category": "HP:0000119", "id": "HP:0010958", "observed": "yes", "label": "Bilateral renal agenesis", "type": "phenotype", "qualifiers": [{"type": "severity", "id": "HP:0012828", "label": "Severe"}]}], "links": {"href": "http://phenotips:8080/rest/patients/P0005042", "rel": "self"}, "nonstandard_features": [], "sex": "M", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:14:08.288Z", "score": 0.3753543937532093, "server": "local-omim"}, "last_modification_date": "2016-06-03T15:22:30.000Z", "id": "P0005042", "ethnicity": {"maternal_ethnicity": ["israeli"], "paternal_ethnicity": ["israeli"]}, "family_history": {}, "date_of_birth": "", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "date": "2016-05-06T18:25:27.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0005042", "notes": {"indication_for_referral": "severe bilateral renal agenesis"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "HIL_B1276_23_A"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005043", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "last_modification_date": "2016-06-03T15:22:52.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:28.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_24_A", "id": "P0005043", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005043"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005040", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "last_modification_date": "2016-06-03T15:23:20.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:26.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_11_A", "id": "P0005040", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005040"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005041", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "F", "last_modification_date": "2016-06-03T15:23:06.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:26.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_12_A", "id": "P0005041", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005041"}		N			CMG_Hildebrandt_Exomes
{"features": [{"category": "HP:0000119", "id": "HP:0010958", "observed": "yes", "label": "Bilateral renal agenesis", "type": "phenotype", "qualifiers": [{"type": "severity", "id": "HP:0012828", "label": "Severe"}]}], "links": {"href": "http://phenotips:8080/rest/patients/P0005042", "rel": "self"}, "nonstandard_features": [], "sex": "M", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-13T06:14:08.288Z", "score": 0.3753543937532093, "server": "local-omim"}, "last_modification_date": "2016-06-03T15:22:30.000Z", "id": "P0005042", "ethnicity": {"maternal_ethnicity": ["israeli"], "paternal_ethnicity": ["israeli"]}, "family_history": {}, "date_of_birth": "", "life_status": "alive", "reporter": "CMG_Hildebrandt_Exomes", "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "date": "2016-05-06T18:25:27.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0005042", "notes": {"indication_for_referral": "severe bilateral renal agenesis"}, "last_modified_by": "CMG_Hildebrandt_Exomes", "solved": {"status": "unsolved"}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "external_id": "HIL_B1276_23_A"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005043", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "last_modification_date": "2016-06-03T15:22:52.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:28.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_24_A", "id": "P0005043", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005043"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005040", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "M", "last_modification_date": "2016-06-03T15:23:20.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:26.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_11_A", "id": "P0005040", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005040"}, {"life_status": "alive", "family_history": {}, "date_of_birth": "", "links": {"href": "http://phenotips:8080/rest/patients/P0005041", "rel": "self"}, "solved": {"status": "unsolved"}, "reporter": "CMG_Hildebrandt_Exomes", "last_modified_by": "CMG_Hildebrandt_Exomes", "sex": "F", "last_modification_date": "2016-06-03T15:23:06.000Z", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "contact": {"user_id": "CMG_Hildebrandt_Exomes", "name": "CMG_Hildebrandt_Exomes", "email": "harindra@broadinstitute.org"}, "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2016-06-03T04:03:00.273Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "date_of_death": "", "prenatal_perinatal_history": {}, "specificity": {"date": "2017-10-13T04:16:00.463Z", "score": 0.0, "server": "monarchinitiative.org"}, "date": "2016-05-06T18:25:26.000Z", "clinicalStatus": {"clinicalStatus": "unaffected"}, "external_id": "HIL_B1276_12_A", "id": "P0005041", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "report_id": "P0005041"}
{"features": [{"observed": "yes", "category": "HP:0025031", "type": "phenotype", "id": "HP:0002032", "label": "Esophageal atresia"}], "links": [{"href": "http://phenotips:8080/rest/patients/P0013806", "rel": "self"}], "nonstandard_features": [], "sex": "M", "meta": {"hgnc_version": "2015-08-09T17:45:23.025Z", "hgncRemote_version": "2017-10-20T04:38:37.787Z", "hpo_version": "releases/2015-09-15", "phenotips_version": "1.2.6", "omim_version": "2015-10-07T18:26:19.654Z"}, "specificity": {"date": "2017-10-21T02:34:38.866Z", "score": 0.46847095713629694, "server": "local-omim"}, "last_modification_date": "2017-10-21T02:34:37.000Z", "id": "P0013806", "ethnicity": {"maternal_ethnicity": [], "paternal_ethnicity": []}, "family_history": {}, "disorders": [{"id": "MIM:105650", "label": "#105650 DIAMOND-BLACKFAN ANEMIA 1; DBA1"}], "date_of_birth": "", "life_status": "alive", "reporter": "1kg", "genes": [], "date_of_death": "", "prenatal_perinatal_phenotype": {"prenatal_phenotype": [], "negative_prenatal_phenotype": []}, "prenatal_perinatal_history": {}, "date": "2017-06-15T14:16:40.000Z", "clinicalStatus": {"clinicalStatus": "affected"}, "report_id": "P0013806", "notes": {"indication_for_referral": "test"}, "last_modified_by": "1kg", "solved": {"status": "unsolved"}, "contact": {"user_id": "1kg", "name": "1kg", "email": "harindra@broadinstitute.org"}, "external_id": "20170615_181613_422805_NA19675"}
"""
