"""
Utility functions for converting Django ORM object to JSON
"""

from __future__ import unicode_literals

import itertools
import json
import logging
import os
from collections import defaultdict
from copy import copy
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import prefetch_related_objects, Prefetch
from django.db.models.fields.files import ImageFieldFile

from reference_data.models import GeneConstraint, dbNSFPGene, Omim, MGI, PrimateAI, HumanPhenotypeOntology
from seqr.models import GeneNote, VariantNote, VariantTag, VariantFunctionalData, SavedVariant
from seqr.views.utils.json_utils import _to_camel_case
from seqr.views.utils.permissions_utils import has_project_permissions
logger = logging.getLogger(__name__)


def _get_json_for_models(models, nested_fields=None, user=None, process_result=None, guid_key=None, additional_model_fields=None):
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
    if additional_model_fields:
        fields += additional_model_fields

    if 'created_by' in fields:
        prefetch_related_objects(models, 'created_by')
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
                    try:
                        field_value = getattr(field_value, field) if field_value else None
                    except ObjectDoesNotExist:
                        field_value = None

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
            'canEdit': has_project_permissions(project, user, can_edit=True),
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


def _get_json_for_families(families, user=None, add_individual_guids_field=False, project_guid=None, skip_nested=False):
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

    prefetch_related_objects(families, 'assigned_analyst')
    prefetch_related_objects(families, 'familyanalysedby_set__created_by')
    if add_individual_guids_field:
        prefetch_related_objects(families, 'individual_set')

    if project_guid or not skip_nested:
        kwargs = {'nested_fields': [{'fields': ('project', 'guid'), 'value': project_guid}]}
    else:
        kwargs = {'additional_model_fields': ['project_id']}

    return _get_json_for_models(families, user=user, process_result=_process_result, **kwargs)


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


def _get_json_for_individuals(individuals, user=None, project_guid=None, family_guid=None, add_sample_guids_field=False,
                              family_fields=None, skip_nested=False, add_hpo_details=False):
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

    def _process_result(result, individual):
        mother = result.pop('mother', None)
        father = result.pop('father', None)

        result.update({
            'caseReviewStatusLastModifiedBy': _get_case_review_status_modified_by(result.get('caseReviewStatusLastModifiedBy')),
            'maternalGuid': mother.guid if mother else None,
            'paternalGuid': father.guid if father else None,
            'maternalId': mother.individual_id if mother else None,
            'paternalId': father.individual_id if father else None,
            'displayName': result['displayName'] or result['individualId'],
        })

        if add_sample_guids_field:
            result['sampleGuids'] = [s.guid for s in individual.sample_set.all()]
            result['igvSampleGuids'] = [s.guid for s in individual.igvsample_set.all()]

    if project_guid or not skip_nested:
        nested_fields = [
            {'fields': ('family', 'guid'), 'value': family_guid},
            {'fields': ('family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
        ]
        if family_fields:
            for field in family_fields:
                nested_fields.append({'fields': ('family', field), 'key': _to_camel_case(field)})
        kwargs = {'nested_fields': nested_fields, 'additional_model_fields': []}
    else:
        kwargs = {'additional_model_fields': ['family_id']}

    if add_hpo_details:
        kwargs['additional_model_fields'] += [
            'features', 'absent_features', 'nonstandard_features', 'absent_nonstandard_features']

    prefetch_related_objects(individuals, 'mother')
    prefetch_related_objects(individuals, 'father')
    prefetch_related_objects(individuals, 'case_review_status_last_modified_by')
    if add_sample_guids_field:
        prefetch_related_objects(individuals, 'sample_set')
        prefetch_related_objects(individuals, 'igvsample_set')

    parsed_individuals = _get_json_for_models(individuals, user=user, process_result=_process_result, **kwargs)
    if add_hpo_details:
        all_hpo_ids = set()
        for i in parsed_individuals:
            all_hpo_ids.update([feature['id'] for feature in i.get('features') or []])
            all_hpo_ids.update([feature['id'] for feature in i.get('absentFeatures') or []])
        hpo_terms_by_id = {hpo.hpo_id: hpo for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_ids)}
        for i in parsed_individuals:
            for feature in i.get('features') or []:
                hpo = hpo_terms_by_id.get(feature['id'])
                if hpo:
                    feature.update({'category': hpo.category_id, 'label': hpo.name})
            for feature in i.get('absentFeatures') or []:
                hpo = hpo_terms_by_id.get(feature['id'])
                if hpo:
                    feature.update({'category': hpo.category_id, 'label': hpo.name})

    return parsed_individuals


def _get_json_for_individual(individual, user=None, **kwargs):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): Django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_model(individual, get_json_for_models=_get_json_for_individuals, user=user, **kwargs)


def get_json_for_samples(samples, project_guid=None, individual_guid=None, skip_nested=False):
    """Returns a JSON representation of the given list of Samples.

    Args:
        samples (array): array of django models for the Samples.
    Returns:
        array: array of json objects
    """

    if project_guid or not skip_nested:
        kwargs = {'nested_fields': [
            {'fields': ('individual', 'guid'), 'value': individual_guid},
            {'fields': ('individual', 'family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
        ]}
    else:
        kwargs = {'additional_model_fields': ['individual_id']}

    return _get_json_for_models(samples, guid_key='sampleGuid', **kwargs)


def get_json_for_sample(sample, **kwargs):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): Django model for the Sample.
    Returns:
        dict: json object
    """

    return _get_json_for_model(sample, get_json_for_models=get_json_for_samples, **kwargs)


def get_json_for_analysis_groups(analysis_groups, project_guid=None, skip_nested=False):
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

    if project_guid or not skip_nested:
        kwargs = {'nested_fields': [{'fields': ('project', 'guid'), 'value': project_guid}]}
    else:
        kwargs = {'additional_model_fields': ['project_id']}

    return _get_json_for_models(analysis_groups, process_result=_process_result, **kwargs)


def get_json_for_analysis_group(analysis_group, **kwargs):
    """Returns a JSON representation of the given AnalysisGroup.

    Args:
        analysis_group (object): Django model for the AnalysisGroup.
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        dict: json object
    """
    return _get_json_for_model(analysis_group, get_json_for_models=get_json_for_analysis_groups, **kwargs)


def get_json_for_saved_variants(saved_variants, add_details=False):
    """Returns a JSON representation of the given variant.
    Args:
        saved_variants (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """
    def _process_result(variant_json, saved_variant):
        if add_details:
            variant_json.update(saved_variant.saved_variant_json)
        variant_json['familyGuids'] = [saved_variant.family.guid]
        return variant_json

    prefetch_related_objects(saved_variants, 'family')

    return _get_json_for_models(saved_variants, guid_key='variantGuid', process_result=_process_result)


def get_json_for_saved_variant(saved_variant, **kwargs):
    """Returns a JSON representation of the given variant.

    Args:
        saved_variant (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """

    return _get_json_for_model(saved_variant, get_json_for_models=get_json_for_saved_variants, **kwargs)


def get_json_for_saved_variants_with_tags(
        saved_variants, include_missing_variants=False, discovery_tags_query=None, **kwargs):

    variants_by_guid = {
        variant['variantGuid']: dict(tagGuids=[], functionalDataGuids=[], noteGuids=[], **variant)
        for variant in get_json_for_saved_variants(saved_variants, **kwargs)
    }

    missing_ids = set()
    saved_variant_id_map = {var.id: var.guid for var in saved_variants}

    variant_tag_id_map = defaultdict(list)
    for tag_mapping in VariantTag.saved_variants.through.objects.filter(savedvariant_id__in=saved_variant_id_map.keys()):
        variant_tag_id_map[tag_mapping.varianttag_id].append(tag_mapping.savedvariant_id)
    tag_models = VariantTag.objects.filter(id__in=variant_tag_id_map.keys())
    tag_id_map = {tag.guid: tag.id for tag in tag_models}

    tags = get_json_for_variant_tags(tag_models, add_variant_guids=False)
    for tag in tags:
        tag_guid = tag['tagGuid']
        tag['variantGuids'] = []
        variant_ids = variant_tag_id_map[tag_id_map[tag_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map.get(variant_id)
            if variant_guid:
                variants_by_guid[variant_guid]['tagGuids'].append(tag['tagGuid'])
                tag['variantGuids'].append(variant_guid)
            else:
                missing_ids.add(variant_id)

    variant_functional_id_map = defaultdict(list)
    for functional_mapping in VariantFunctionalData.saved_variants.through.objects.filter(
            savedvariant_id__in=saved_variant_id_map.keys()):
        variant_functional_id_map[functional_mapping.variantfunctionaldata_id].append(functional_mapping.savedvariant_id)
    functional_models = VariantFunctionalData.objects.filter(id__in=variant_functional_id_map.keys())
    functional_id_map = {tag.guid: tag.id for tag in functional_models}

    functional_data = get_json_for_variant_functional_data_tags(functional_models, add_variant_guids=False)
    for tag in functional_data:
        tag_guid = tag['tagGuid']
        tag['variantGuids'] = []
        variant_ids = variant_functional_id_map[functional_id_map[tag_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map.get(variant_id)
            if variant_guid:
                variants_by_guid[variant_guid]['functionalDataGuids'].append(tag['tagGuid'])
                tag['variantGuids'].append(variant_guid)
            else:
                missing_ids.add(variant_id)

    variant_note_id_map = defaultdict(list)
    for note_mapping in VariantNote.saved_variants.through.objects.filter(savedvariant_id__in=saved_variant_id_map.keys()):
        variant_note_id_map[note_mapping.variantnote_id].append(note_mapping.savedvariant_id)
    note_models = VariantNote.objects.filter(id__in=variant_note_id_map.keys())
    note_id_map = {note.guid: note.id for note in note_models}

    notes = get_json_for_variant_notes(note_models, add_variant_guids=False)
    for note in notes:
        note_guid = note['noteGuid']
        note['variantGuids'] = []
        variant_ids = variant_note_id_map[note_id_map[note_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map.get(variant_id)
            if variant_guid:
                variants_by_guid[variant_guid]['noteGuids'].append(note['noteGuid'])
                note['variantGuids'].append(variant_guid)
            else:
                missing_ids.add(variant_id)

    if include_missing_variants and missing_ids:
        variants_by_guid.update({
            variant['variantGuid']: dict(tagGuids=[], functionalDataGuids=[], noteGuids=[], **variant)
            for variant in get_json_for_saved_variants(SavedVariant.objects.filter(id__in=missing_ids), **kwargs)
        })

    response = {
        'variantTagsByGuid': {tag['tagGuid']: tag for tag in tags},
        'variantNotesByGuid': {note['noteGuid']: note for note in notes},
        'variantFunctionalDataByGuid': {tag['tagGuid']: tag for tag in functional_data},
        'savedVariantsByGuid': variants_by_guid,
    }

    if discovery_tags_query:
        from seqr.views.utils.variant_utils import get_variant_key

        discovery_saved_variant_by_guid = {
            var.guid: var for var in SavedVariant.objects.filter(discovery_tags_query).prefetch_related('family', 'family__project')}
        discovery_tags = get_json_for_variant_tags(VariantTag.objects.filter(
            variant_tag_type__category='CMG Discovery Tags',
            saved_variants__in=discovery_saved_variant_by_guid.values()
        ))
        if discovery_tags:
            families = set()
            response['discoveryTags'] = defaultdict(list)
            for tag in discovery_tags:
                for variant_guid in tag.pop('variantGuids'):
                    variant = discovery_saved_variant_by_guid.get(variant_guid)
                    if variant:
                        families.add(variant.family)
                        tag_json = {'savedVariant': {
                            'variantGuid': variant.guid,
                            'familyGuid': variant.family.guid,
                            'projectGuid': variant.family.project.guid,
                        }}
                        tag_json.update(tag)
                        variant_key = get_variant_key(
                            genomeVersion=variant.family.project.genome_version,
                            xpos=variant.xpos, ref=variant.ref, alt=variant.alt,
                        )
                        response['discoveryTags'][variant_key].append(tag_json)
            response['familiesByGuid'] = {f['familyGuid']: f for f in _get_json_for_families(list(families))}

    return response


def get_json_for_variant_tags(tags, add_variant_guids=True):
    """Returns a JSON representation of the given variant tags.

    Args:
        tag (object): Django models for the VariantTag.
    Returns:
        dict: json objects
    """
    def _process_result(tag_json, tag):
        if add_variant_guids:
            tag_json['variantGuids'] = [variant.guid for variant in tag.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(tags, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    nested_fields = [{'fields': ('variant_tag_type', field), 'key': field} for field in ['name', 'category', 'color']]
    return _get_json_for_models(tags, nested_fields=nested_fields, guid_key='tagGuid', process_result=_process_result)


def get_json_for_variant_functional_data_tags(tags, add_variant_guids=True):
    """Returns a JSON representation of the given variant tags.

    Args:
        tags (object): Django models for the VariantFunctionalData.
    Returns:
        dict: json objects
    """

    def _process_result(tag_json, tag):
        display_data = json.loads(tag.get_functional_data_tag_display())
        tag_json.update({
            'name': tag_json.pop('functionalDataTag'),
            'metadataTitle': display_data.get('metadata_title'),
            'color': display_data['color'],
        })
        if add_variant_guids:
            tag_json['variantGuids'] = [variant.guid for variant in tag.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(tags, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    return _get_json_for_models(tags, guid_key='tagGuid', process_result=_process_result)


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


def get_json_for_variant_notes(notes, add_variant_guids=True):
    """Returns a JSON representation of the given variant notes.

    Args:
        notes (object): Django model for the VariantNote.
    Returns:
        dict: json objects
    """
    def _process_result(note_json, note):
        if add_variant_guids:
            note_json['variantGuids'] = [variant.guid for variant in note.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(notes, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    return _get_json_for_models(notes, guid_key='noteGuid', process_result=_process_result)


def get_json_for_variant_note(note, **kwargs):
    """Returns a JSON representation of the given variant note.

    Args:
        note (object): Django model for the VariantNote.
    Returns:
        dict: json object
    """

    return _get_json_for_model(note, get_json_for_models=get_json_for_variant_notes, **kwargs)


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


def get_json_for_locus_lists(locus_lists, user, include_genes=False, include_project_count=False):
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
        if include_project_count:
            result['numProjects'] = locus_list.num_projects
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


def get_json_for_project_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = list(get_project_collaborators_by_username(project).values())

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
        prefetch_related_objects(genes, Prefetch('dbnsfpgene_set', queryset=dbNSFPGene.objects.only('gene__gene_id', *dbNSFPGene._meta.json_fields)))
    if add_omim:
        prefetch_related_objects(genes, Prefetch('omim_set', queryset=Omim.objects.only('gene__gene_id', *Omim._meta.json_fields)))
    if add_constraints:
        prefetch_related_objects(genes, Prefetch('geneconstraint_set', queryset=GeneConstraint.objects.order_by('-mis_z', '-pLI').only('gene__gene_id', *GeneConstraint._meta.json_fields)))
    if add_primate_ai:
        prefetch_related_objects(genes, Prefetch('primateai_set', queryset=PrimateAI.objects.only('gene__gene_id', *PrimateAI._meta.json_fields)))
    if add_mgi:
        prefetch_related_objects(genes, Prefetch('mgi_set', queryset=MGI.objects.only('gene__gene_id', 'marker_id')))

    return _get_json_for_models(genes, process_result=_process_result)


def get_json_for_gene(gene, **kwargs):
    """Returns a JSON representation of the given GeneInfo.

    Args:
        gene (object): Django model for the GeneInfo.
    Returns:
        dict: json object
    """

    return _get_json_for_model(gene, get_json_for_models=get_json_for_genes, **kwargs)


def get_json_for_saved_searches(searches, user):
    def _process_result(result, search):
        # Do not apply HGMD filters in shared searches for non-staff users
        if not search.created_by and not user.is_staff and result['search'].get('pathogenicity', {}).get('hgmd'):
            result['search']['pathogenicity'] = {
                k: v for k, v in result['search']['pathogenicity'].items() if k != 'hgmd'
            }
    prefetch_related_objects(searches, 'created_by')
    return _get_json_for_models(searches, guid_key='savedSearchGuid', process_result=_process_result)


def get_json_for_saved_search(search, user):
    return _get_json_for_model(search, user=user, get_json_for_models=get_json_for_saved_searches)


def get_json_for_matchmaker_submissions(models, individual_guid=None, additional_model_fields=None, all_parent_guids=False):
    nested_fields = [{'fields': ('individual', 'guid'), 'value': individual_guid}]
    if all_parent_guids:
        nested_fields += [
            {'fields': ('individual', 'individual_id'), 'key': 'individualId'},
            {'fields': ('individual', 'family', 'guid'), 'key': 'familyGuid'},
            {'fields': ('individual', 'family', 'project', 'guid'), 'key': 'projectGuid'},
        ]
    return _get_json_for_models(
        models, nested_fields=nested_fields, guid_key='submissionGuid', additional_model_fields=additional_model_fields
    )


def get_json_for_matchmaker_submission(submission, **kwargs):
    return _get_json_for_model(submission, get_json_for_models=get_json_for_matchmaker_submissions, **kwargs)