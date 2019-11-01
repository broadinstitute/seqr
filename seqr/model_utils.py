import logging
import traceback

from collections import defaultdict
from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from django.utils import timezone

from seqr.models import Sample, Individual, Family
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.json_utils import _to_snake_case
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual, \
    ProjectTag as BaseProjectTag, VariantTag as BaseVariantTag, VariantNote as BaseVariantNote, \
    VariantFunctionalData as BaseVariantFunctionalData, GeneNote as BaseGeneNote, AnalysedBy as BaseAnalysedBy, \
    FamilyGroup as BaseFamilyGroup, VCFFile, ProjectGeneList, ProjectCollaborator
from xbrowse_server.gene_lists.models import GeneList as BaseGeneList, GeneListItem as BaseGeneListItem
from xbrowse_server.mall import get_datastore, get_reference
from xbrowse_server.search_cache.utils import clear_project_results_cache
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.base.lookups import get_variants_from_variant_tuples

SEQR_TO_XBROWSE_CLASS_MAPPING = {
    "Project": BaseProject,
    "Family": BaseFamily,
    "Individual": BaseIndividual,
    "VariantTagType": BaseProjectTag,
    "VariantTag": BaseVariantTag,
    "VariantFunctionalData": BaseVariantFunctionalData,
    "VariantNote": BaseVariantNote,
    "LocusList": BaseGeneList,
    "LocusListGene": BaseGeneListItem,
    "GeneNote": BaseGeneNote,
    "FamilyAnalysedBy": BaseAnalysedBy,
    "AnalysisGroup": BaseFamilyGroup,
}

_DELETED_FIELD = "__DELETED__"

SEQR_TO_XBROWSE_FIELD_MAPPING = {
    "Project": {
        "name": "project_name",
        'deprecated_project_id': 'project_id',
        "has_new_search": _DELETED_FIELD,
    },
    "Family": {
        "display_name": "family_name",
        "description": "short_description",
        "analysis_notes": "about_family_content",
        "analysis_summary": "analysis_summary_content",
    },
    "Individual": {
        "individual_id": "indiv_id",
        "sex": "gender",
        "display_name": "nickname",
        "phenotips_eid": "phenotips_id",
        "notes": "other_notes",
        "mother": "maternal_id",
        "father": "paternal_id",
        "filter_flags": _DELETED_FIELD,
        "pop_platform_filters": _DELETED_FIELD,
        "population": _DELETED_FIELD,
    },
    "VariantTagType": {
        "name": "tag",
        "description": "title",
    },
    "SavedVariant": {
        "xpos_start": "xpos",
    },
    "VariantTag": {
        "variant_tag_type": "project_tag",
        "created_by": "user",
        "search_parameters": "search_url",
        "search_hash": _DELETED_FIELD,
    },
    "VariantNote": {
        "created_by": "user",
        "search_parameters": "search_url",
        "search_hash": _DELETED_FIELD,
    },
    "VariantFunctionalData": {
        "created_by": "user",
        "search_parameters": "search_url",
        "search_hash": _DELETED_FIELD,
    },
    "LocusList": {
        "created_by": "owner",
        "last_modified_by": "last_updated",
    },
    "LocusListGene": {
        "locus_list": "gene_list",
        "created_by": _DELETED_FIELD,
    },
    "GeneNote": {
        "created_by": "user",
    },
    "FamilyAnalysedBy": {
        "created_by": "user",
    },
    "AnalysisGroup": {
        "created_by": _DELETED_FIELD,
    },
}

FLATTENED_MODEL_FIELDS = {
    'Individual': {
        'maternal_id':  {'field': 'individual_id'},
        'paternal_id':  {'field': 'individual_id'},
    },
    'VariantTag': {
        'saved_variant': {'fields': ['xpos_start', 'ref', 'alt', 'family']}
    },
    'VariantFunctionalData': {
        'saved_variant': {'fields': ['xpos_start', 'ref', 'alt', 'family']}
    },
    'VariantNote': {
        'saved_variant': {'fields': ['xpos_start', 'ref', 'alt', 'family', 'project']}
    },
}

NON_NULL_MODEL_FIELDS = {
    'AnalysisGroup': {'description': ''}
}


def _update_model(model_obj, **kwargs):
    for field, value in kwargs.items():
        setattr(model_obj, field, value)

    model_obj.save()


def _is_seqr_model(obj):
    return type(obj).__module__ == "seqr.models"


def find_matching_xbrowse_model(seqr_model):
    logging.info("find matching xbrowse %s for %s" % (type(seqr_model).__name__, seqr_model))
    if not _is_seqr_model(seqr_model):
        raise ValueError("Unexpected model class: %s.%s" % (type(seqr_model).__module__, type(seqr_model).__name__))

    try:
        seqr_class_name = type(seqr_model).__name__

        if seqr_class_name == "Project":
            return BaseProject.objects.get(
                Q(seqr_project=seqr_model) |
                (Q(seqr_project__isnull=True) &
                 Q(project_id=seqr_model.deprecated_project_id)))
        elif seqr_class_name == "Family":
            return BaseFamily.objects.get(
                Q(seqr_family=seqr_model) |
                (Q(seqr_family__isnull=True) &
                 Q(project__project_id=seqr_model.project.deprecated_project_id) &
                 Q(family_id=seqr_model.family_id)))
        elif seqr_class_name == "Individual":
            return BaseIndividual.objects.get(
                Q(seqr_individual=seqr_model) |
                (Q(seqr_individual__isnull=True) &
                 Q(family__project__project_id=seqr_model.family.project.deprecated_project_id) &
                 Q(family__family_id=seqr_model.family.family_id) &
                 Q(indiv_id=seqr_model.individual_id)))
        elif seqr_class_name == "VariantTagType":
            return BaseProjectTag.objects.get(
                Q(project__project_id=seqr_model.project.deprecated_project_id) &
                (Q(seqr_variant_tag_type=seqr_model) |
                 Q(seqr_variant_tag_type__isnull=True,
                   tag=seqr_model.name,
                   category=seqr_model.category,
                   project__project_id=seqr_model.project.deprecated_project_id))
                )
        elif seqr_class_name == "VariantTag":
            match_filter = Q(
                seqr_variant_tag__isnull=True,
                project_tag__project__project_id=seqr_model.saved_variant.family.project.deprecated_project_id,
                project_tag__tag=seqr_model.variant_tag_type.name,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(
                    family__family_id=seqr_model.saved_variant.family.family_id,
                )
            return BaseVariantTag.objects.get(Q(seqr_variant_tag=seqr_model) | match_filter)
        elif seqr_class_name == "VariantFunctionalData":
            match_filter = Q(
                seqr_variant_functional_data__isnull=True,
                functional_data_tag=seqr_model.functional_data_tag,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(
                    family__family_id=seqr_model.saved_variant.family.family_id,
                    family__project__project_id=seqr_model.saved_variant.family.project.deprecated_project_id,
                )
            return BaseVariantFunctionalData.objects.get(Q(seqr_variant_functional_data=seqr_model) | match_filter)
        elif seqr_class_name == "VariantNote":
            match_filter = Q(
                seqr_variant_note__isnull=True,
                note=seqr_model.note,
                project__project_id=seqr_model.saved_variant.family.project.deprecated_project_id,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(family__family_id=seqr_model.saved_variant.family.family_id)
            return BaseVariantNote.objects.get(Q(seqr_variant_note=seqr_model) | match_filter)
        elif seqr_class_name == "LocusList":
            return BaseGeneList.objects.get(
                Q(seqr_locus_list=seqr_model) |
                (Q(seqr_locus_list__isnull=True) &
                 Q(name=seqr_model.name) &
                 Q(description=seqr_model.description) &
                 Q(owner=seqr_model.created_by) &
                 Q(is_public=seqr_model.is_public)))
        elif seqr_class_name == "LocusListGene":
            return BaseGeneListItem.objects.get(
                gene_list=find_matching_xbrowse_model(seqr_model.locus_list),
                description=seqr_model.description or '',
                gene_id=seqr_model.gene_id)
        elif seqr_class_name == "GeneNote":
            return BaseGeneNote.objects.get(
                note=seqr_model.note,
                gene_id=seqr_model.gene_id,
            )
        elif seqr_class_name == "FamilyAnalysedBy":
            return BaseAnalysedBy.objects.get(seqr_family_analysed_by=seqr_model)
        elif seqr_class_name == "AnalysisGroup":
            return BaseFamilyGroup.objects.get(
                Q(seqr_analysis_group=seqr_model) |
                (Q(seqr_analysis_group__isnull=True) &
                 Q(name=seqr_model.name) &
                 Q(project__project_id=seqr_model.project.deprecated_project_id)))
    except Exception as e:
        logging.error("ERROR: when looking up xbrowse model for seqr %s model: %s" % (seqr_model, e))
        #traceback.print_exc()

    return None


def convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs):
    # rename fields
    seqr_class_name = type(seqr_model).__name__
    field_mapping = SEQR_TO_XBROWSE_FIELD_MAPPING[seqr_class_name]
    xbrowse_kwargs = {
        field_mapping.get(field, field): value for field, value in kwargs.items()
        if not field_mapping.get(field, field) == _DELETED_FIELD
    }
    for field, default_value in NON_NULL_MODEL_FIELDS.get(seqr_class_name, {}).items():
        if field in xbrowse_kwargs and xbrowse_kwargs[field] is None:
            xbrowse_kwargs[field] = default_value

    if seqr_class_name == "Individual" and "family" in xbrowse_kwargs:
        xbrowse_kwargs["project"] = getattr(seqr_model, "family").project

    if seqr_class_name in ["LocusList", "AnalysisGroup"] and 'name' in xbrowse_kwargs:
        xbrowse_kwargs['slug'] = seqr_model.guid

    # handle foreign keys
    for key, value in xbrowse_kwargs.items():
        if _is_seqr_model(value):
            if key in FLATTENED_MODEL_FIELDS.get(seqr_class_name, {}):
                nested_config = FLATTENED_MODEL_FIELDS[seqr_class_name][key]
                if nested_config.get('fields'):
                    nested_model_kwargs = {k: getattr(value, k, None) for k in nested_config['fields']}
                    xbrowse_kwargs.update(convert_seqr_kwargs_to_xbrowse_kwargs(value, **nested_model_kwargs))
                    del xbrowse_kwargs[key]
                elif nested_config.get('field'):
                    xbrowse_kwargs[key] = getattr(value, nested_config['field'], None)
            else:
                if key == 'project_tag':
                    value.project = seqr_model.saved_variant.family.project
                new_value = find_matching_xbrowse_model(value)
                if new_value is not None:
                    xbrowse_kwargs[key] = new_value
                else:
                    logging.info("ERROR: unable to find equivalent seqr model for %s: %s" % (key, value))
                    del xbrowse_kwargs[key]

    # Explicitly add timestamps
    xbrowse_model_class = SEQR_TO_XBROWSE_CLASS_MAPPING.get(seqr_class_name)
    for timestamp_key in ['date_saved', 'last_updated']:
        if xbrowse_model_class and hasattr(xbrowse_model_class, timestamp_key) and timestamp_key not in xbrowse_kwargs:
            xbrowse_kwargs[timestamp_key] = timezone.now()

    return xbrowse_kwargs


def update_seqr_model(seqr_model, **kwargs):
    logging.info("update_seqr_model(%s, %s)" % (seqr_model, kwargs))
    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    _update_model(seqr_model, **kwargs)

    if not xbrowse_model:
        return

    xbrowse_kwargs = convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs)

    _update_model(xbrowse_model, **xbrowse_kwargs)


def _create_xbrowse_model(seqr_model, **kwargs):
    try:
        seqr_model_class = seqr_model.__class__
        seqr_model_class_name = seqr_model_class.__name__
        xbrowse_kwargs = convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs)
        xbrowse_model_class = SEQR_TO_XBROWSE_CLASS_MAPPING[seqr_model_class_name]
        xbrowse_model_class_name = xbrowse_model_class.__name__
        logging.info("_create_xbrowse_model(%s, %s)" % (xbrowse_model_class_name, xbrowse_kwargs))
        xbrowse_model = xbrowse_model_class.objects.create(**xbrowse_kwargs)

        seqr_model_foreign_key_name = "seqr_"+_to_snake_case(seqr_model_class_name)
        if hasattr(xbrowse_model, seqr_model_foreign_key_name):
            setattr(xbrowse_model, seqr_model_foreign_key_name, seqr_model)
            xbrowse_model.save()
        return xbrowse_model

    except Exception as e:
        logging.error("ERROR: error when creating xbrowse model %s: %s" % (seqr_model, e))
        traceback.print_exc()
        return None


def create_seqr_model(seqr_model_class, **kwargs):
    logging.info("create_seqr_model(%s, %s)" % (seqr_model_class.__name__, kwargs))
    seqr_model = seqr_model_class.objects.create(**kwargs)
    _create_xbrowse_model(seqr_model, **kwargs)

    return seqr_model


def get_or_create_seqr_model(seqr_model_class, **kwargs):
    logging.info("get_or_create_seqr_model(%s, %s)" % (seqr_model_class, kwargs))
    seqr_model, created = seqr_model_class.objects.get_or_create(**kwargs)

    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    if created or xbrowse_model is None:
        if xbrowse_model is not None:
            logging.error("ERROR: created seqr model: %s while xbrowse model already exists: %s" % (seqr_model, xbrowse_model))
        elif seqr_model_class.__name__ not in SEQR_TO_XBROWSE_CLASS_MAPPING:
            logging.error("ERROR: create operation not implemented for seqr model: %s" % (seqr_model_class.__name__))
        else:
            _create_xbrowse_model(seqr_model, **kwargs)

    return seqr_model, created


def delete_seqr_model(seqr_model):
    logging.info("delete_seqr_model(%s)" % seqr_model)
    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    seqr_model.delete()

    if xbrowse_model:
        try:
            xbrowse_model.delete()
        except Exception as e:
            logging.error("ERROR: error when deleting seqr model %s: %s" % (seqr_model, e))
            traceback.print_exc()


# model-specific functions
def update_xbrowse_vcfffiles(project, sample_type, elasticsearch_index, dataset_path, matched_sample_id_to_sample_record):
    base_project = find_matching_xbrowse_model(project)
    get_datastore(base_project).bust_project_cache(base_project.project_id)
    clear_project_results_cache(base_project.project_id)

    vcf_file = VCFFile.objects.filter(
        project=base_project,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_type=sample_type,
        elasticsearch_index=elasticsearch_index).order_by('-pk').first()

    if not vcf_file:
        vcf_file = VCFFile.objects.create(
            project=base_project,
            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            sample_type=sample_type,
            elasticsearch_index=elasticsearch_index,
        )
        logging.info("Created vcf file: " + str(vcf_file.__dict__))

    vcf_file.file_path = dataset_path
    vcf_file.loaded_date = matched_sample_id_to_sample_record.values()[0].loaded_date
    vcf_file.save()

    for indiv in [s.individual for s in matched_sample_id_to_sample_record.values()]:
        for base_indiv in BaseIndividual.objects.filter(seqr_individual=indiv).only('id'):
            base_indiv.vcf_files.add(vcf_file)


def add_xbrowse_project_gene_lists(project, locus_lists):
    xbrowse_project = find_matching_xbrowse_model(project)
    for locus_list in locus_lists:
        xbrowse_gene_list = find_matching_xbrowse_model(locus_list)
        if xbrowse_project and xbrowse_gene_list:
            ProjectGeneList.objects.get_or_create(project=xbrowse_project, gene_list=xbrowse_gene_list)


def remove_xbrowse_project_gene_lists(project, locus_lists):
    xbrowse_project = find_matching_xbrowse_model(project)
    for locus_list in locus_lists:
        xbrowse_gene_list = find_matching_xbrowse_model(locus_list)
        if xbrowse_project and xbrowse_gene_list:
            ProjectGeneList.objects.filter(project=xbrowse_project, gene_list=xbrowse_gene_list).delete()


def create_xbrowse_project_collaborator(project, user, collaborator_type=None):
    base_project = find_matching_xbrowse_model(project)
    if base_project:
        collab, _ = ProjectCollaborator.objects.get_or_create(user=user, project=base_project)
        if collaborator_type:
            collab.collaborator_type = collaborator_type
            collab.save()


def delete_xbrowse_project_collaborator(project, user):
    base_project = find_matching_xbrowse_model(project)
    if base_project:
        ProjectCollaborator.objects.get(user=user, project=base_project).delete()


def update_xbrowse_family_group_families(analysis_group, families):
    base_family_group = find_matching_xbrowse_model(analysis_group)
    if base_family_group:
        base_family_group.families.set(BaseFamily.objects.filter(seqr_family__in=families))


def deprecated_retrieve_saved_variants_json(project, variant_tuples, create_if_missing):
    project_id = project.deprecated_project_id
    xbrowse_project = BaseProject.objects.get(project_id=project_id)
    user = User.objects.filter(is_staff=True).first()  # HGMD annotations are only returned for staff users

    variants = get_variants_from_variant_tuples(xbrowse_project, variant_tuples, user=user)
    if not create_if_missing:
        variants = [var for var in variants if not var.get_extra('created_variant')]
    add_extra_info_to_variants_project(get_reference(), xbrowse_project, variants, add_populations=True)

    family_guids_by_id = {f.family_id: f.guid for f in Family.objects.filter(project=project)}
    individual_guids_by_id = {i.individual_id: i.guid for i in Individual.objects.filter(family__project=project)}
    return [_variant_details(variant.toJSON(), family_guids_by_id, individual_guids_by_id) for variant in variants]


def _variant_details(variant_json, family_guids_by_id, individual_guids_by_id):
    annotation = variant_json.get('annotation') or {}
    is_es_variant = annotation.get('db') == 'elasticsearch'

    chrom, pos = get_chrom_pos(variant_json['xpos'])

    extras = variant_json.get('extras') or {}
    genome_version = extras.get('genome_version') or '37'
    lifted_over_genome_version = '37' if genome_version == '38' else '38'
    coords_field = 'grch%s_coords' % lifted_over_genome_version
    coords = extras.get(coords_field).split('-') if extras.get(coords_field) else []
    lifted_over_chrom = coords[0].lstrip('chr') if len(coords) > 0 else ''
    lifted_over_pos = coords[1] if len(coords) > 1 else ''

    genotypes = {
        individual_id: {
            'ab': genotype.get('ab'),
            'ad': genotype.get('extras', {}).get('ad'),
            'cnvs': {
                'array': genotype.get('extras', {}).get('cnvs', {}).get('array'),
                'caller': genotype.get('extras', {}).get('cnvs', {}).get('caller'),
                'cn': genotype.get('extras', {}).get('cnvs', {}).get('cn'),
                'freq': genotype.get('extras', {}).get('cnvs', {}).get('freq'),
                'LRR_median': genotype.get('extras', {}).get('cnvs', {}).get('LRR_median'),
                'LRR_sd': genotype.get('extras', {}).get('cnvs', {}).get('LRR_sd'),
                'size': genotype.get('extras', {}).get('cnvs', {}).get('size'),
                'snps': genotype.get('extras', {}).get('cnvs', {}).get('snps'),
                'type': genotype.get('extras', {}).get('cnvs', {}).get('type'),
            },
            'dp': genotype.get('extras', {}).get('dp'),
            'gq': genotype.get('gq'),
            'numAlt': genotype.get('num_alt'),
            'pl': genotype.get('extras', {}).get('pl'),
            'sampleId': individual_id,
        } for individual_id, genotype in variant_json.get('genotypes', {}).items()
    }

    genotypes = {individual_guids_by_id.get(individual_id): genotype for individual_id, genotype in
                 genotypes.items()
                 if individual_guids_by_id.get(individual_id)}

    transcripts = defaultdict(list)
    for i, vep_a in enumerate(annotation.get('vep_annotation') or []):
        transcripts[vep_a.get('gene', vep_a.get('gene_id'))].append(
            _transcript_detail(vep_a, i == annotation.get('worst_vep_annotation_index')))

    return {
        'chrom': chrom,
        'pos': pos,
        'predictions': {
            'cadd': annotation.get('cadd_phred'),
            'dann': annotation.get('dann_score'),
            'eigen': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'gerp_rs': annotation.get('GERP_RS'),
            'phastcons_100_vert': annotation.get('phastCons100way_vertebrate'),
            'mpc': annotation.get('mpc_score'),
            'metasvm': annotation.get('metasvm'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'primate_ai': annotation.get('primate_ai_score'),
            'revel': annotation.get('revel_score'),
            'sift': annotation.get('sift'),
            'splice_ai': annotation.get('splice_ai_delta_score'),
        },
        'mainTranscriptId': _variant_main_transcript_id(variant_json),
        'clinvar': {
            'clinicalSignificance': extras.get('clinvar_clinsig'),
            'variationId': extras.get('clinvar_variant_id'),
            'alleleId': extras.get('clinvar_allele_id'),
            'goldStars': extras.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class'),
        },
        'familyGuids': [family_guids_by_id[variant_json['extras']['family_id']]],
        'genotypes': genotypes,
        'genotypeFilters': next((genotype.get('filter') for genotype in variant_json.get('genotypes', {}).values()), None),
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'originalAltAlleles': extras.get('orig_alt_alleles') or [],
        'populations': {
            'callset': {
                'af': annotation.get('freqs', {}).get('AF'),
                'ac': annotation.get('pop_counts', {}).get('AC'),
                'an': annotation.get('pop_counts', {}).get('AN'),
            },
            'topmed': {
                'af': annotation.get('freqs', {}).get('topmed_AF'),
                'ac': annotation.get('pop_counts', {}).get('topmed_AC'),
                'an': annotation.get('pop_counts', {}).get('topmed_AN'),
            },
            'g1k': {
                'af': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'ac': annotation.get('pop_counts', {}).get('g1kAC'),
                'an': annotation.get('pop_counts', {}).get('g1kAN'),
            },
            'exac': {
                'af': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'ac': annotation.get('pop_counts', {}).get('exac_v3_AC'),
                'an': annotation.get('pop_counts', {}).get('exac_v3_AN'),
                'hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
            },
            'gnomad_exomes': {
                'af': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax',
                                     annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_exomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
            },
            'gnomad_genomes': {
                'af': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_genomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
        },
        'rsid': annotation.get('rsid'),
        'transcripts': transcripts,
        'xpos': variant_json['xpos'],
        'ref': variant_json['ref'],
        'alt': variant_json['alt'],
    }


def _variant_main_transcript_id(variant_json):
    annotation = variant_json.get('annotation') or {}
    main_transcript = annotation.get('main_transcript') or (
        annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get(
            'worst_vep_annotation_index') is not None and annotation['vep_annotation'] else {})
    return main_transcript.get('feature') or main_transcript.get('transcript_id')


def _transcript_detail(transcript, isChosenTranscript):
    return {
        'transcriptId': transcript.get('feature') or transcript.get('transcript_id'),
        'transcriptRank': 0 if isChosenTranscript else transcript.get('transcript_rank', 100),
        'geneId': transcript.get('gene') or transcript.get('gene_id'),
        'geneSymbol': transcript.get('gene_symbol') or transcript.get('symbol'),
        'lof': transcript.get('lof'),
        'lofFlags': transcript.get('lof_flags'),
        'lofFilter': transcript.get('lof_filter'),
        'aminoAcids': transcript.get('amino_acids'),
        'biotype': transcript.get('biotype'),
        'canonical': transcript.get('canonical'),
        'cdnaPosition': transcript.get('cdna_position') or transcript.get('cdna_start'),
        'codons': transcript.get('codons'),
        'majorConsequence': transcript.get('consequence') or transcript.get('major_consequence'),
        'hgvsc': transcript.get('hgvsc'),
        'hgvsp': transcript.get('hgvsp'),
    }
