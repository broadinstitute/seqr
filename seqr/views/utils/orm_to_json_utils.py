"""
Utility functions for converting Django ORM object to JSON
"""

import itertools
import json
import logging
import os
from collections import defaultdict
from copy import copy
from django.db.models import prefetch_related_objects, Prefetch
from django.db.models.fields.files import ImageFieldFile
from guardian.shortcuts import get_objects_for_group

from reference_data.models import GeneConstraint, dbNSFPGene
from seqr.models import CAN_VIEW, CAN_EDIT, Sample, GeneNote, VariantFunctionalData, LocusList
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.json_utils import _to_camel_case
logger = logging.getLogger(__name__)


def _get_json_for_models(models, nested_fields=None, user=None, process_result=None, guid_key=None):
    """Returns an array JSON representations of the given models.

    Args:
        models (array): Array of django models
        user (object): Django User object for determining whether to include restricted/internal-only fields
        nested_fields (array): Optional array of fields to get from the model that are nested on related objects
        process_result (lambda): Optional function to post-process a given model json
        guid_key (string): Optional key to use for the model's guid
    Returns:
        array: json objects
    """

    if not models:
        return []

    model_class = type(models[0])
    fields = copy(model_class._meta.json_fields)
    if user and user.is_staff:
        fields += getattr(model_class._meta, 'internal_json_fields', [])

    for nested_field in nested_fields or []:
        if not nested_field.get('value'):
            prefetch_related_objects(models, '__'.join(nested_field['fields'][:-1]))

    results = []
    for model in models:
        result = {_to_camel_case(field): getattr(model, field) for field in fields}
        for nested_field in (nested_fields or []):
            field_value = nested_field.get('value')
            if not field_value:
                field_value = model
                for field in nested_field['fields']:
                    field_value = getattr(field_value, field) if field_value else None
            result[nested_field.get('key', _to_camel_case('_'.join(nested_field['fields'])))] = field_value

        if result.get('guid'):
            guid_key = guid_key or '{}{}Guid'.format(model_class.__name__[0].lower(), model_class.__name__[1:])
            result[guid_key] = result.pop('guid')
        if result.get('createdBy'):
            result['createdBy'] = result['createdBy'].get_full_name() or result['createdBy'].email
        if process_result:
            process_result(result, model)
        results.append(result)

    return results


def _get_json_for_model(model, get_json_for_models=_get_json_for_models, **kwargs):
    """Helper function to return a JSON representations of the given model.

    Args:
        model (object): Django models
        get_json_for_models (lambda): Function used to determine the json for an array of the given model
    Returns:
        object: json object
    """
    return get_json_for_models([model], **kwargs)[0]


def _get_empty_json_for_model(model_class):
    return {_to_camel_case(field): None for field in model_class._meta.json_fields}


def get_json_for_sample_dict(sample_dict):
    """Returns a JSON representation of the given Sample dictionary.

        Args:
            sample (object): dictionary representation for the Sample.
        Returns:
            dict: json object
        """
    result = {_to_camel_case(field): sample_dict.get('sample_{}'.format(field)) for field in Sample._meta.json_fields}

    result.update({
        'projectGuid': sample_dict['project_guid'],
        'individualGuid': sample_dict['individual_guid'],
        'sampleGuid': result.pop('guid'),
    })
    return result


def _get_json_for_user(user):
    """Returns JSON representation of the given User object

    Args:
        user (object): Django user model

    Returns:
        dict: json object
    """

    if hasattr(user, '_wrapped'):
        user = user._wrapped   # Django request.user actually stores the Django User objects in a ._wrapped attribute

    user_json = {_to_camel_case(field): getattr(user, field) for field in
                ['username', 'email', 'first_name', 'last_name', 'last_login', 'is_staff', 'date_joined', 'id']}
    user_json['displayName'] = user.get_full_name()
    return user_json


def get_json_for_projects(projects, user=None, add_project_category_guids_field=True):
    """Returns JSON representation of the given Projects.

    Args:
        projects (object array): Django models for the projects
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    def _process_result(result, project):
        result.update({
            'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()] if add_project_category_guids_field else [],
            'canEdit': user.is_staff or user.has_perm(CAN_EDIT, project),
        })

    if add_project_category_guids_field:
        prefetch_related_objects(projects, 'projectcategory_set')

    return _get_json_for_models(projects, user=user, process_result=_process_result)


def _get_json_for_project(project, user, **kwargs):
    """Returns JSON representation of the given Project.

    Args:
        project (object): Django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_model(project, get_json_for_models=get_json_for_projects, user=user, **kwargs)


def _get_json_for_families(families, user=None, add_individual_guids_field=False, project_guid=None):
    """Returns a JSON representation of the given Family.

    Args:
        families (array): array of django models representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
        project_guid (boolean): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        array: json objects
    """

    def _get_pedigree_image_url(pedigree_image):
        if isinstance(pedigree_image, ImageFieldFile):
            try:
                pedigree_image = pedigree_image.url
            except Exception:
                pedigree_image = None
        return os.path.join("/media/", pedigree_image) if pedigree_image else None

    def _process_result(result, family):
        result['analysedBy'] = [{
            'createdBy': {'fullName': ab.created_by.get_full_name(), 'email': ab.created_by.email, 'isStaff': ab.created_by.is_staff},
            'lastModifiedDate': ab.last_modified_date,
        } for ab in family.familyanalysedby_set.all()]
        pedigree_image = _get_pedigree_image_url(result.pop('pedigreeImage'))
        result['pedigreeImage'] = pedigree_image
        if add_individual_guids_field:
            result['individualGuids'] = [i.guid for i in family.individual_set.all()]
        if not result['displayName']:
            result['displayName'] = result['familyId']
        if result['assignedAnalyst']:
            result['assignedAnalyst'] = {
                'fullName': result['assignedAnalyst'].get_full_name(),
                'email': result['assignedAnalyst'].email,
            }
        else:
            result['assignedAnalyst'] = None
    prefetch_related_objects(families, 'familyanalysedby_set__created_by')
    if add_individual_guids_field:
        prefetch_related_objects(families, 'individual_set')

    nested_fields = [{'fields': ('project', 'guid'), 'value': project_guid}]

    return _get_json_for_models(families, nested_fields=nested_fields, user=user, process_result=_process_result)


def _get_json_for_family(family, user=None, **kwargs):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): Django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        dict: json object
    """

    return _get_json_for_model(family, get_json_for_models=_get_json_for_families, user=user, **kwargs)


def _get_json_for_individuals(individuals, user=None, project_guid=None, family_guid=None, add_sample_guids_field=False, family_fields=None):
    """Returns a JSON representation for the given list of Individuals.

    Args:
        individuals (array): array of django models for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
        family_guid (boolean): An optional field to use as the familyGuid instead of querying the DB
        add_sample_guids_field (boolean): A flag to indicate weather sample ids should be added
    Returns:
        array: array of json objects
    """

    def _get_case_review_status_modified_by(modified_by):
        return modified_by.email or modified_by.username if hasattr(modified_by, 'email') else modified_by

    def _load_phenotips_data(phenotips_data):
        phenotips_json = None
        if phenotips_data:
            try:
                phenotips_json = json.loads(phenotips_data)
            except Exception as e:
                logger.error("Couldn't parse phenotips: {}".format(e))
        return phenotips_json

    def _process_result(result, individual):
        mother = result.pop('mother', None)
        father = result.pop('father', None)

        result.update({
            'caseReviewStatusLastModifiedBy': _get_case_review_status_modified_by(result.get('caseReviewStatusLastModifiedBy')),
            'phenotipsData': _load_phenotips_data(result['phenotipsData']),
            'maternalGuid': mother.guid if mother else None,
            'paternalGuid': father.guid if father else None,
            'maternalId': mother.individual_id if mother else None,
            'paternalId': father.individual_id if father else None,
            'displayName': result['displayName'] or result['individualId'],
        })

        if add_sample_guids_field:
            result['sampleGuids'] = [s.guid for s in individual.sample_set.all()]

    nested_fields = [
        {'fields': ('family', 'guid'), 'value': family_guid},
        {'fields': ('family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
    ]
    if family_fields:
        for field in family_fields:
            nested_fields.append({'fields': ('family', field), 'key': _to_camel_case(field)})

    prefetch_related_objects(individuals, 'mother')
    prefetch_related_objects(individuals, 'father')
    prefetch_related_objects(individuals, 'case_review_status_last_modified_by')
    if add_sample_guids_field:
        prefetch_related_objects(individuals, 'sample_set')

    return _get_json_for_models(individuals, nested_fields=nested_fields, user=user, process_result=_process_result)


def _get_json_for_individual(individual, user=None, **kwargs):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): Django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_model(individual, get_json_for_models=_get_json_for_individuals, user=user, **kwargs)


def get_json_for_samples(samples, project_guid=None, individual_guid=None):
    """Returns a JSON representation of the given list of Samples.

    Args:
        samples (array): array of django models for the Samples.
    Returns:
        array: array of json objects
    """

    nested_fields = [
        {'fields': ('individual', 'guid'), 'value': individual_guid},
        {'fields': ('individual', 'family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
    ]

    return _get_json_for_models(samples, nested_fields=nested_fields)


def get_json_for_sample(sample, **kwargs):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): Django model for the Sample.
    Returns:
        dict: json object
    """

    return _get_json_for_model(sample, get_json_for_models=get_json_for_samples, **kwargs)


def get_json_for_analysis_groups(analysis_groups, project_guid=None):
    """Returns a JSON representation of the given list of AnalysisGroups.

    Args:
        analysis_groups (array): array of django models for the AnalysisGroups.
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        array: array of json objects
    """

    def _process_result(result, group):
        result.update({
            'familyGuids': [f.guid for f in group.families.all()]
        })

    prefetch_related_objects(analysis_groups, 'families')

    nested_fields = [{'fields': ('project', 'guid'), 'value': project_guid}]

    return _get_json_for_models(analysis_groups, nested_fields=nested_fields, process_result=_process_result)


def get_json_for_analysis_group(analysis_group, **kwargs):
    """Returns a JSON representation of the given AnalysisGroup.

    Args:
        analysis_group (object): Django model for the AnalysisGroup.
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        dict: json object
    """
    return _get_json_for_model(analysis_group, get_json_for_models=get_json_for_analysis_groups, **kwargs)


def get_json_for_saved_variants(saved_variants, add_tags=False, add_details=False):
    """Returns a JSON representation of the given variant.

    Args:
        saved_variant (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """
    def _process_result(variant_json, saved_variant):
        if add_tags:
            variant_json.update({
                'tags': [get_json_for_variant_tag(tag) for tag in saved_variant.varianttag_set.all()],
                'functionalData': [get_json_for_variant_functional_data(tag) for tag in
                                   saved_variant.variantfunctionaldata_set.all()],
                'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()],
            })
        if add_details:
            variant_json.update(saved_variant.saved_variant_json)
        if 'variantId' not in variant_json:
            chrom, pos = get_chrom_pos(saved_variant.xpos)
            variant_json['variantId'] = '{}-{}-{}-{}'.format(chrom, pos, saved_variant.ref, saved_variant.alt)
        variant_json['familyGuids'] = [saved_variant.family.guid]
        return variant_json

    prefetch_related_objects(saved_variants, 'family')
    if add_tags:
        prefetch_related_objects(saved_variants, 'varianttag_set__variant_tag_type', 'varianttag_set__created_by',
                                 'variantnote_set__created_by', 'variantfunctionaldata_set__created_by')

    return _get_json_for_models(saved_variants, guid_key='variantGuid', process_result=_process_result)


def get_json_for_saved_variant(saved_variant, **kwargs):
    """Returns a JSON representation of the given variant.

    Args:
        saved_variant (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """

    return _get_json_for_model(saved_variant, get_json_for_models=get_json_for_saved_variants, **kwargs)


def get_json_for_variant_tag(tag):
    """Returns a JSON representation of the given variant tag.

    Args:
        tag (object): Django model for the VariantTag.
    Returns:
        dict: json object
    """

    nested_fields = [{'fields': ('variant_tag_type', field), 'key': field} for field in ['name', 'category', 'color']]
    return _get_json_for_model(tag, nested_fields=nested_fields, guid_key='tagGuid')


def get_json_for_variant_functional_data(tag):
    """Returns a JSON representation of the given variant tag.

    Args:
        tag (object): Django model for the VariantFunctionalData.
    Returns:
        dict: json object
    """

    result = _get_json_for_model(tag, guid_key='tagGuid')

    display_data = json.loads(tag.get_functional_data_tag_display())
    result.update({
        'name': result.pop('functionalDataTag'),
        'metadataTitle': display_data.get('metadata_title'),
        'color': display_data['color'],
    })
    return result


def get_json_for_variant_functional_data_tag_types():
    functional_tag_types = []
    for category, tags in VariantFunctionalData.FUNCTIONAL_DATA_CHOICES:
        functional_tag_types += [{
            'category': category,
            'name': name,
            'metadataTitle': json.loads(tag_json).get('metadata_title'),
            'color': json.loads(tag_json)['color'],
            'description': json.loads(tag_json).get('description'),
        } for name, tag_json in tags]
    return functional_tag_types


def get_json_for_variant_note(note):
    """Returns a JSON representation of the given variant note.

    Args:
        note (object): Django model for the VariantNote.
    Returns:
        dict: json object
    """

    return _get_json_for_model(note, guid_key='noteGuid')


def get_json_for_gene_notes(notes, user):
    """Returns a JSON representation of the given gene note.

    Args:
        note (object): Django model for the GeneNote.
    Returns:
        dict: json object
    """

    def _process_result(result, note):
        result.update({
            'editable': user.is_staff or user == note.created_by,
        })

    return _get_json_for_models(notes, user=user, guid_key='noteGuid', process_result=_process_result)


def get_json_for_gene_note(note, user):
    """Returns a JSON representation of the given gene note.

    Args:
        note (object): Django model for the GeneNote.
    Returns:
        dict: json object
    """

    return _get_json_for_model(note, user=user, get_json_for_models=get_json_for_gene_notes)


def get_json_for_gene_notes_by_gene_id(gene_ids, user):
    """Returns a JSON representation of the gene notes for the given gene ids.

    Args:
        note (object): Django model for the GeneNote.
    Returns:
        dict: json object
    """
    notes_by_gene_id = defaultdict(list)
    for note in get_json_for_gene_notes(GeneNote.objects.filter(gene_id__in=gene_ids), user):
        notes_by_gene_id[note['geneId']].append(note)
    return notes_by_gene_id


def get_json_for_locus_lists(locus_lists, user, include_genes=False):
    """Returns a JSON representation of the given LocusLists.

    Args:
        locus_lists (array): array of LocusList django models.
    Returns:
        array: json objects
    """

    def _process_result(result, locus_list):
        gene_set = locus_list.locuslistgene_set
        interval_set = locus_list.locuslistinterval_set
        if include_genes:
            intervals = _get_json_for_models(interval_set.all())
            genome_versions = {interval['genomeVersion'] for interval in intervals}
            result.update({
                'items': [{'geneId': gene.gene_id} for gene in gene_set.all()] + intervals,
                'intervalGenomeVersion': genome_versions.pop() if len(genome_versions) == 1 else None,
            })
        result.update({
            'numEntries': gene_set.count() + interval_set.count(),
            'canEdit': user == locus_list.created_by,
        })

    prefetch_related_objects(locus_lists, 'created_by')
    prefetch_related_objects(locus_lists, 'locuslistgene_set')
    prefetch_related_objects(locus_lists, 'locuslistinterval_set')

    return _get_json_for_models(locus_lists, user=user, process_result=_process_result)


def get_json_for_locus_list(locus_list, user):
    """Returns a JSON representation of the given LocusList.

    Args:
        locus_list (object): LocusList django model.
    Returns:
        dict: json object
    """
    return _get_json_for_model(locus_list, get_json_for_models=get_json_for_locus_lists, user=user, include_genes=True)


def get_project_locus_list_models(project):
    return get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList)


def get_sorted_project_locus_lists(project, user):
    result = get_json_for_locus_lists(get_project_locus_list_models(project), user)
    return sorted(result, key=lambda locus_list: locus_list['name'])


def get_json_for_project_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = get_project_collaborators_by_username(project).values()

    return sorted(collaborator_list, key=lambda collaborator: (collaborator['lastName'], collaborator['displayName']))


def get_project_collaborators_by_username(project, include_permissions=True):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborators = {}

    for collaborator in project.can_view_group.user_set.all():
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=False
        )

    for collaborator in itertools.chain(project.owners_group.user_set.all(), project.can_edit_group.user_set.all()):
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=True
        )

    return collaborators


def _get_collaborator_json(collaborator, include_permissions, can_edit):
    collaborator_json = _get_json_for_user(collaborator)
    if include_permissions:
        collaborator_json.update({
            'hasViewPermissions': True,
            'hasEditPermissions': can_edit,
        })
    return collaborator_json


def get_json_for_genes(genes, user=None, add_dbnsfp=False, add_omim=False, add_constraints=False, add_notes=False,
                       add_primate_ai=False, add_mgi=False):
    """Returns a JSON representation of the given list of GeneInfo.

    Args:
        genes (array): array of django models for the GeneInfo.
    Returns:
        array: array of json objects
    """
    total_gene_constraints = GeneConstraint.objects.count()
    if add_notes:
        gene_notes_json = get_json_for_gene_notes_by_gene_id([gene.gene_id for gene in genes], user)

    def _add_total_constraint_count(result, *args):
        result['totalGenes'] = total_gene_constraints

    def _process_result(result, gene):
        if add_dbnsfp:
            # prefetching only works with all()
            dbnsfp = next((dbnsfp for dbnsfp in gene.dbnsfpgene_set.all()), None)
            if dbnsfp:
                result.update(_get_json_for_model(dbnsfp))
            else:
                result.update(_get_empty_json_for_model(dbNSFPGene))
        if add_primate_ai:
            # prefetching only works with all()
            primate_ai = next((primate_ai for primate_ai in gene.primateai_set.all()), None)
            if primate_ai:
                result['primateAi'] = _get_json_for_model(primate_ai)
        if add_mgi:
            # prefetching only works with all()
            mgi = next((mgi for mgi in gene.mgi_set.all()), None)
            result['mgiMarkerId'] = mgi.marker_id if mgi else None
        if add_omim:
            omim_phenotypes = _get_json_for_models(gene.omim_set.all())
            result['omimPhenotypes'] = [phenotype for phenotype in omim_phenotypes if phenotype['phenotypeMimNumber']]
            result['mimNumber'] = omim_phenotypes[0]['mimNumber'] if omim_phenotypes else None
        if add_constraints:
            constraint = next((constraint for constraint in gene.geneconstraint_set.all()), None)
            result['constraints'] = _get_json_for_model(constraint, process_result=_add_total_constraint_count) if constraint else {}
        if add_notes:
            result['notes'] = gene_notes_json.get(result['geneId'], [])

    if add_dbnsfp:
        prefetch_related_objects(genes, 'dbnsfpgene_set')
    if add_omim:
        prefetch_related_objects(genes, 'omim_set')
    if add_constraints:
        prefetch_related_objects(genes, Prefetch('geneconstraint_set', queryset=GeneConstraint.objects.order_by('-mis_z', '-pLI')))
    if add_primate_ai:
        prefetch_related_objects(genes, 'primateai_set')
    if add_mgi:
        prefetch_related_objects(genes, 'mgi_set')

    return _get_json_for_models(genes, process_result=_process_result)


def get_json_for_gene(gene, **kwargs):
    """Returns a JSON representation of the given GeneInfo.

    Args:
        gene (object): Django model for the GeneInfo.
    Returns:
        dict: json object
    """

    return _get_json_for_model(gene, get_json_for_models=get_json_for_genes, **kwargs)


def get_json_for_saved_searches(search, user):
    def _process_result(result, search):
        # Do not apply HGMD filters in shared searches for non-staff users
        if not search.created_by and not user.is_staff and result['search'].get('pathogenicity', {}).get('hgmd'):
            result['search']['pathogenicity'] = {
                k: v for k, v in result['search']['pathogenicity'].items() if k != 'hgmd'
            }
    return _get_json_for_models(search, guid_key='savedSearchGuid', process_result=_process_result)


def get_json_for_saved_search(search, user):
    return _get_json_for_model(search, user=user, get_json_for_models=get_json_for_saved_searches)