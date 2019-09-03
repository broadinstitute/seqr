"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

import json
import logging

from reference_data.models import HumanPhenotypeOntology
from seqr.model_utils import delete_seqr_model
from seqr.models import Sample, Individual
from seqr.views.utils.pedigree_image_utils import update_pedigree_images
from seqr.views.utils.phenotips_utils import delete_phenotips_patient, PhenotipsException
from seqr.views.utils.export_table_utils import export_table


logger = logging.getLogger(__name__)

_SEX_TO_EXPORTED_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORTED_VALUE['U'] = ''

__AFFECTED_TO_EXPORTED_VALUE = dict(Individual.AFFECTED_STATUS_LOOKUP)
__AFFECTED_TO_EXPORTED_VALUE['U'] = ''


def delete_individuals(project, individual_guids):
    """Delete one or more individuals

    Args:
        project (object): Django ORM model for project
        individual_guids (list): GUIDs of individuals to delete

    Returns:
        list: Family objects for families with deleted individuals
    """

    individuals_to_delete = Individual.objects.filter(
        family__project=project, guid__in=individual_guids)

    samples_to_delete = Sample.objects.filter(
        individual__family__project=project, individual__guid__in=individual_guids)

    for sample in samples_to_delete:
        logger.info("Deleting sample: %s" % sample)
        sample.delete()

    families = {}
    for individual in individuals_to_delete:
        families[individual.family.family_id] = individual.family

        # delete phenotips records
        try:
            delete_phenotips_patient(project, individual)
        except (PhenotipsException, ValueError) as e:
            logger.error("Error: couldn't delete patient from phenotips: {} {} ({})".format(
                individual.phenotips_eid, individual, e))

        # delete Individual
        delete_seqr_model(individual)

    update_pedigree_images(families.values())

    families_with_deleted_individuals = list(families.values())

    return families_with_deleted_individuals


def export_individuals(
    filename_prefix,
    individuals,
    file_format,

    include_project_name=False,
    include_project_created_date=False,
    include_display_name=False,
    include_created_date=False,
    include_case_review_status=False,
    include_case_review_last_modified_date=False,
    include_case_review_last_modified_by=False,
    include_case_review_discussion=False,
    include_analysis_status=False,
    include_coded_phenotype=False,
    include_hpo_terms_present=False,
    include_hpo_terms_absent=False,
    include_paternal_ancestry=False,
    include_maternal_ancestry=False,
    include_age_of_onset=False,
    include_first_loaded_date=False,
):
    """Export Individuals table.

    Args:
        filename_prefix (string): Filename without the file extension.
        individuals (list): List of Django Individual objects to include in the table
        file_format (string): "xls" or "tsv"

    Returns:
        Django HttpResponse object with the table data as an attachment.
    """

    header = []
    if include_project_name:
        header.append('Project')
    if include_project_created_date:
        header.append('Project Created Date')

    header.extend([
        'Family ID',
        'Individual ID',
        'Paternal ID',
        'Maternal ID',
        'Sex',
        'Affected Status',
        'Notes',
    ])

    if include_display_name:
        header.append('Display Name')
    if include_created_date:
        header.append('Created Date')
    if include_case_review_status:
        header.append('Case Review Status')
    if include_case_review_last_modified_date:
        header.append('Case Review Status Last Modified')
    if include_case_review_last_modified_by:
        header.append('Case Review Status Last Modified By')
    if include_case_review_discussion:
        header.append('Case Review Discussion')
    if include_analysis_status:
        header.append('Analysis Status')
    if include_coded_phenotype:
        header.append('Coded Phenotype')
    if include_hpo_terms_present:
        header.append('HPO Terms (present)')
    if include_hpo_terms_absent:
        header.append('HPO Terms (absent)')
    if include_paternal_ancestry:
        header.append('Paternal Ancestry')
    if include_maternal_ancestry:
        header.append('Maternal Ancestry')
    if include_age_of_onset:
        header.append('Age of Onset')
    if include_project_created_date:
        header.append('First Data Loaded Date')

    rows = []
    for i in individuals:
        row = []
        if include_project_name:
            row.extend([i.family.project.name or i.family.project.project_id])
        if include_project_created_date:
            row.append(i.family.project.created_date)

        row.extend([
            i.family.family_id,
            i.individual_id,
            i.father.individual_id if i.father else None,
            i.mother.individual_id if i.mother else None,
            _SEX_TO_EXPORTED_VALUE.get(i.sex),
            __AFFECTED_TO_EXPORTED_VALUE.get(i.affected),
            i.notes,  # TODO should strip markdown (or be moved to client-side export)
        ])

        if include_display_name:
            row.append(i.display_name)
        if include_created_date:
            row.append(i.created_date)
        if include_case_review_status:
            row.append(Individual.CASE_REVIEW_STATUS_LOOKUP.get(i.case_review_status, ''))
        if include_case_review_last_modified_date:
            row.append(i.case_review_status_last_modified_date)
        if include_case_review_last_modified_by:
            row.append(_user_to_string(i.case_review_status_last_modified_by))
        if include_case_review_discussion:
            row.append(i.case_review_discussion)
        if include_analysis_status:
            row.append(i.family.analysis_status)
        if include_coded_phenotype:
            row.append(i.family.coded_phenotype)

        if (include_hpo_terms_present or \
            include_hpo_terms_absent or \
            include_paternal_ancestry or \
            include_maternal_ancestry or \
            include_age_of_onset):
            if i.phenotips_data:
                phenotips_json = json.loads(i.phenotips_data)
                phenotips_fields = _parse_phenotips_data(phenotips_json)
            else:
                phenotips_fields = {}

            if include_hpo_terms_present:
                row.append(phenotips_fields.get('phenotips_features_present', ''))
            if include_hpo_terms_absent:
                row.append(phenotips_fields.get('phenotips_features_absent', ''))
            if include_paternal_ancestry:
                row.append(phenotips_fields.get('paternal_ancestry', ''))
            if include_maternal_ancestry:
                row.append(phenotips_fields.get('maternal_ancestry', ''))
            if include_age_of_onset:
                row.append(phenotips_fields.get('age_of_onset', ''))

        if include_first_loaded_date:
            first_loaded_sample = i.sample_set.filter(
                dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
                loaded_date__isnull=False,
            ).order_by('loaded_date').first()
            row.append(first_loaded_sample.loaded_date if first_loaded_sample else None)

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def _user_to_string(user):
    """Takes a Django User object and returns a string representation"""
    if not user:
        return ''

    return user.email or user.username


def _parse_phenotips_data(phenotips_json):
    """Takes a phenotips_json dictionary for a single Individual and converts it to a more convenient
    representation which is a flat dictionary of key-value pairs with the following keys:

        phenotips_features_present
        phenotips_features_absent
        previously_tested_genes
        candidate_genes
        paternal_ancestry
        maternal_ancestry
        age_of_onset
        ...

    Args:
        phenotips_json (dict): The PhenoTips json from an Individual

    Returns:
        dict: flat dictionary of key-value pairs
    """

    result = {
        'phenotips_features_present': '',
        'phenotips_features_absent': '',
        'previously_tested_genes': '',
        'candidate_genes': '',
        'paternal_ancestry': '',
        'maternal_ancestry': '',
        'age_of_onset': '',
    }

    features = phenotips_json.get('features')
    if features:
        if any(feature for feature in features if not feature.get('label')):
            all_hpo_terms = [feature['id'] for feature in features]
            hpo_terms = {hpo.hpo_id: hpo for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_terms)}
            for feature in features:
                hpo_data = hpo_terms.get(feature['id'])
                if hpo_data:
                    feature['label'] = hpo_data.name
                else:
                    feature['label'] = feature['id']

        result['phenotips_features_present'] = []
        result['phenotips_features_absent'] = []
        for feature in features:
            if feature.get('observed') == 'yes':
                result['phenotips_features_present'].append(feature['label'])
            elif feature.get('observed') == 'no':
                result['phenotips_features_absent'].append(feature['label'])
        result['phenotips_features_present'] = ', '.join(result['phenotips_features_present'])
        result['phenotips_features_absent'] = ', '.join(result['phenotips_features_absent'])

    if phenotips_json.get('rejectedGenes'):
        result['previously_tested_genes'] = []
        for gene in phenotips_json.get('rejectedGenes'):
            result['previously_tested_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['previously_tested_genes'] = ', '.join(result['previously_tested_genes'])

    if phenotips_json.get('genes'):
        result['candidate_genes'] = []
        for gene in phenotips_json.get('genes'):
            result['candidate_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['candidate_genes'] = ', '.join(result['candidate_genes'])

    if phenotips_json.get('ethnicity'):
        ethnicity = phenotips_json.get('ethnicity')
        if ethnicity.get('paternal_ethnicity'):
            result['paternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

        if ethnicity.get('maternal_ethnicity'):
            result['maternal_ancestry'] = ", ".join(ethnicity.get('maternal_ethnicity'))

    if phenotips_json.get('global_age_of_onset'):
        result['age_of_onset'] = ", ".join((a.get('label') for a in phenotips_json.get('global_age_of_onset') if a))

    return result
