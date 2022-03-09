from matchmaker.matchmaker_utils import get_mme_genes_phenotypes_for_submissions, parse_mme_features, \
    parse_mme_gene_variants, get_mme_metrics
from matchmaker.models import MatchmakerSubmission
from seqr.models import Family, VariantTagType, SavedVariant, RnaSeqTpm
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required
from seqr.views.utils.variant_utils import get_variants_response
from settings import ANALYST_PROJECT_CATEGORY

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

    response_json = get_variants_response(
        request, saved_variant_models, add_all_context=True, include_igv=False, add_locus_list_detail=True,
        include_missing_variants=True, include_rna_seq=False,
    )

    return create_json_response(response_json)

@login_and_policies_required
def rna_seq_expression(request, gene, tissues):
    response = {}
    for tissue in tissues.split(','):
        response[tissue] = list(RnaSeqTpm.objects.filter(sample__tissue_type=tissue, gene_id=gene).values_list('tpm', flat=True))

    return create_json_response(response)
