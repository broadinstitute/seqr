from datetime import datetime
from django.db.models import Q, prefetch_related_objects
import json
from random import randint

from matchmaker.matchmaker_utils import get_mme_gene_phenotype_ids_for_submissions, parse_mme_features, \
    get_mme_metrics, get_hpo_terms_by_id
from matchmaker.models import MatchmakerSubmission
from seqr.models import Family, VariantTagType, SavedVariant, FamilyAnalysedBy
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions, get_json_for_saved_variants
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required
from seqr.views.utils.variant_utils import get_variants_response

MAX_SAVED_VARIANTS = 10000


@login_and_policies_required
def mme_details(request):
    submissions = MatchmakerSubmission.objects.filter(deleted_date__isnull=True).filter(
        individual__family__project__guid__in=get_project_guids_user_can_view(request.user))

    hpo_ids, gene_ids, submission_gene_variants = get_mme_gene_phenotype_ids_for_submissions(
        submissions, get_gene_variants=True)
    genes_by_id = get_genes(gene_ids)
    hpo_terms_by_id = get_hpo_terms_by_id(hpo_ids)

    submission_json = get_json_for_matchmaker_submissions(
        submissions, additional_model_fields=['label'], all_parent_guids=True)
    submissions_by_guid = {s['submissionGuid']: s for s in submission_json}

    for submission in submissions:
        gene_variants = submission_gene_variants[submission.guid]
        submissions_by_guid[submission.guid].update({
            'phenotypes': parse_mme_features(submission.features, hpo_terms_by_id),
            'geneVariants': gene_variants,
            'geneSymbols': ','.join({genes_by_id.get(gv['geneId'], {}).get('geneSymbol') for gv in gene_variants})
        })

    saved_variants = get_json_for_saved_variants(
        SavedVariant.objects.filter(matchmakersubmissiongenes__matchmaker_submission__guid__in=submissions_by_guid),
        add_details=True,
    )

    response = {
        'submissions': list(submissions_by_guid.values()),
        'genesById': genes_by_id,
        'savedVariantsByGuid': {s['variantGuid']: s for s in saved_variants},
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
    families = families.filter(project__guid__in=get_project_guids_user_can_view(request.user)).order_by('family_id')

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
        include_rna_seq=False, include_project_name=True,
    )

    return create_json_response(response_json)


@analyst_required
def bulk_update_family_analysed_by(request):
    request_json = json.loads(request.body)
    data_type =request_json['dataType']
    family_upload_data = load_uploaded_file(request_json['familiesFile']['uploadedFileId'])
    header = [col.split()[0].lower() for col in family_upload_data[0]]
    if not ('project' in header and 'family' in header):
        return create_json_response({'error': 'Project and Family columns are required'}, status=400)
    families_data = [dict(zip(header, row)) for row in family_upload_data[1:]]

    family_qs = [Q(family_id=row['family'], project__name=row['project']) for row in families_data]
    family_filter_q = family_qs[0]
    for f_q in family_qs[1:]:
        family_filter_q |= f_q
    families = Family.objects.filter(family_filter_q)

    warnings = []
    if len(families) < len(families_data):
        prefetch_related_objects(families, 'project')
        family_models_set = {(f.family_id, f.project.name) for f in families}
        requested_family_set = {(row['family'], row['project']) for row in families_data}
        missing_families = ', '.join([f'{fam[0]} ({fam[1]})' for fam in sorted(requested_family_set - family_models_set)])
        warnings.append(f'No match found for the following families: {missing_families}')

    analysed_by_models = [
        FamilyAnalysedBy(family=family, data_type=data_type, last_modified_date=datetime.now())
        for family in families
    ]
    for ab in analysed_by_models:
        ab.guid = f'FAB{randint(10**5, 10**6)}_{ab}'[:FamilyAnalysedBy.MAX_GUID_SIZE] # nosec
    FamilyAnalysedBy.bulk_create(request.user, analysed_by_models)

    return create_json_response({
        'warnings': warnings,
        'info': [f'Updated "analysed by" for {len(families)} families'],
    })
