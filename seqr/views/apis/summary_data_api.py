from django.db.models import prefetch_related_objects, Q
import logging

from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_submissions, parse_mme_features, \
    parse_mme_gene_variants, get_mme_metrics
from matchmaker.models import MatchmakerSubmission
from seqr.views.apis.saved_variant_api import _add_locus_lists
from seqr.models import Family, LocusList, VariantTagType, SavedVariant, Individual
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, get_json_for_saved_variants_with_tags, \
    get_json_for_variant_functional_data_tag_types, get_json_for_projects, _get_json_for_families, \
    get_json_for_locus_lists, _get_json_for_models, get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required
from seqr.views.utils.variant_utils import saved_variant_genes
from settings import ANALYST_PROJECT_CATEGORY

logger = logging.getLogger(__name__)

MAX_SAVED_VARIANTS = 10000


@login_and_policies_required
def mme_details(request):
    submissions = MatchmakerSubmission.objects.filter(deleted_date__isnull=True).filter(
        individual__family__project__guid__in=get_project_guids_user_can_view(request.user))

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

    response = {
        'submissions': list(submissions_by_guid.values()),
        'genesById': genes_by_id,
    }
    if user_is_analyst(request.user):
        response['metrics'] = get_mme_metrics()

    return create_json_response(response)


@analyst_required
def success_story(request, success_story_types):
    if success_story_types == 'all':
        families = Family.objects.filter(success_story__isnull=False)
    else:
        success_story_types = success_story_types.split(',')
        families = Family.objects.filter(success_story_types__overlap=success_story_types)
    families = families.filter(project__projectcategory__name=ANALYST_PROJECT_CATEGORY).order_by('family_id')

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


@login_and_policies_required
def saved_variants_page(request, tag):
    gene = request.GET.get('gene')
    if tag == 'ALL':
        saved_variant_models = SavedVariant.objects.exclude(varianttag=None)
    else:
        tag_type = VariantTagType.objects.get(name=tag, project__isnull=True)
        saved_variant_models = SavedVariant.objects.filter(varianttag__variant_tag_type=tag_type)

    saved_variant_models = saved_variant_models.filter(family__project__guid__in=get_project_guids_user_can_view(request.user))

    if gene:
        saved_variant_models = saved_variant_models.filter(saved_variant_json__transcripts__has_key=gene)
    elif saved_variant_models.count() > MAX_SAVED_VARIANTS:
        return create_json_response({'error': 'Select a gene to filter variants'}, status=400)

    prefetch_related_objects(saved_variant_models, 'family__project')
    response_json = get_json_for_saved_variants_with_tags(saved_variant_models, add_details=True, include_missing_variants=True)

    project_models_by_guid = {variant.family.project.guid: variant.family.project for variant in saved_variant_models}
    families = {variant.family for variant in saved_variant_models}
    individuals = Individual.objects.filter(family__in=families)

    saved_variants = list(response_json['savedVariantsByGuid'].values())
    genes = saved_variant_genes(saved_variants)
    locus_lists_by_guid = _add_locus_lists(list(project_models_by_guid.values()), genes, include_all_lists=True)

    projects_json = get_json_for_projects(list(project_models_by_guid.values()), user=request.user, add_project_category_guids_field=False)
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
            'locusListGuids': list(locus_lists_by_guid.keys()),
            'variantTagTypes': sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order'] or 0),
            'variantFunctionalTagTypes': functional_tag_types,
        })

    families_json = _get_json_for_families(list(families), user=request.user, add_individual_guids_field=True)
    individuals_json = _get_json_for_individuals(individuals, add_hpo_details=True, user=request.user)
    for locus_list in get_json_for_locus_lists(LocusList.objects.filter(guid__in=locus_lists_by_guid.keys()), request.user):
        locus_lists_by_guid[locus_list['locusListGuid']].update(locus_list)

    response_json.update({
        'genesById': genes,
        'projectsByGuid': {project['projectGuid']: project for project in projects_json},
        'familiesByGuid': {family['familyGuid']: family for family in families_json},
        'individualsByGuid': {indiv['individualGuid']: indiv for indiv in individuals_json},
        'locusListsByGuid': locus_lists_by_guid,
    })
    return create_json_response(response_json)
