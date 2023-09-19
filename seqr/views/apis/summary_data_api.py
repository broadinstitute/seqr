from datetime import datetime
from django.db.models import CharField, F, Value, Case, When
from django.db.models.functions import Coalesce, Concat, JSONObject, NullIf
import json
from random import randint

from matchmaker.matchmaker_utils import get_mme_gene_phenotype_ids_for_submissions, parse_mme_features, \
    get_mme_metrics, get_hpo_terms_by_id
from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology
from seqr.models import Family, Individual, VariantTagType, SavedVariant, FamilyAnalysedBy
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions, get_json_for_saved_variants,\
    add_individual_hpo_details, INDIVIDUAL_DISPLAY_NAME_EXPR
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required, get_project_and_check_permissions, get_internal_projects
from seqr.views.utils.anvil_metadata_utils import get_loaded_before_date_project_individual_samples, parse_anvil_metadata, \
    DISCOVERY_TABLE_CORE_COLUMNS, DISCOVERY_TABLE_VARIANT_COLUMNS
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
        tags = tag.split(';')
        tag_types = VariantTagType.objects.filter(name__in=tags, project__isnull=True)
        saved_variant_models = SavedVariant.objects.all()
        for tt in tag_types:
            saved_variant_models = saved_variant_models.filter(varianttag__variant_tag_type=tt).distinct()

    saved_variant_models = saved_variant_models.filter(family__project__guid__in=get_project_guids_user_can_view(request.user))

    if gene:
        saved_variant_models = saved_variant_models.filter(saved_variant_json__transcripts__has_key=gene)
    elif saved_variant_models.count() > MAX_SAVED_VARIANTS:
        return create_json_response({'error': 'Select a gene to filter variants'}, status=400)

    response_json = get_variants_response(
        request, saved_variant_models, add_all_context=True, include_igv=False, add_locus_list_detail=True,
        include_individual_gene_scores=False, include_project_name=True,
    )

    return create_json_response(response_json)


@login_and_policies_required
def hpo_summary_data(request, hpo_id):
    data = Individual.objects.filter(
        family__project__guid__in=get_project_guids_user_can_view(request.user),
        features__contains=[{'id': hpo_id}],
    ).order_by('id').values(
        'features', individualGuid=F('guid'), displayName=INDIVIDUAL_DISPLAY_NAME_EXPR, familyId=F('family__family_id'),
         familyData=JSONObject(
            projectGuid=F('family__project__guid'),
            genomeVersion=F('family__project__genome_version'),
            familyGuid=F('family__guid'),
            analysisStatus=F('family__analysis_status'),
            displayName=Coalesce(NullIf('family__display_name', Value('')), 'family__family_id'),
        ))
    add_individual_hpo_details(data)

    return create_json_response({'data': list(data)})


@analyst_required
def bulk_update_family_analysed_by(request):
    request_json = json.loads(request.body)
    data_type =request_json['dataType']
    family_upload_data = load_uploaded_file(request_json['familiesFile']['uploadedFileId'])
    header = [col.split()[0].lower() for col in family_upload_data[0]]
    if not ('project' in header and 'family' in header):
        return create_json_response({'error': 'Project and Family columns are required'}, status=400)
    requested_families = {(row[header.index('project')], row[header.index('family')]) for row in family_upload_data[1:]}

    family_db_id_lookup = {
        (f['project__name'], f['family_id']): f['id'] for f in Family.objects.annotate(
            project_family=Concat('project__name', 'family_id', output_field=CharField())
        ).filter(project_family__in=[f'{project}{family}' for project, family in requested_families])
        .values('id', 'family_id', 'project__name')
    }

    warnings = []
    missing_from_db = requested_families - set(family_db_id_lookup.keys())
    if missing_from_db:
        missing_families = ', '.join([f'{family} ({project})' for project, family in sorted(missing_from_db)])
        warnings.append(f'No match found for the following families: {missing_families}')

    analysed_by_models = [
        FamilyAnalysedBy(family_id=family_db_id_lookup[family_key], data_type=data_type, last_modified_date=datetime.now())
        for family_key in requested_families if family_key in family_db_id_lookup
    ]
    for ab in analysed_by_models:
        ab.guid = f'FAB{randint(10**5, 10**6)}_{ab}'[:FamilyAnalysedBy.MAX_GUID_SIZE] # nosec
    FamilyAnalysedBy.bulk_create(request.user, analysed_by_models)

    return create_json_response({
        'warnings': warnings,
        'info': [f'Updated "analysed by" for {len(analysed_by_models)} families'],
    })


# TODO change access
@analyst_required
def sample_metadata_export(request, project_guid):
    is_all_projects = project_guid == 'all'
    omit_airtable = is_all_projects or 'true' in request.GET.get('omitAirtable', '')
    if is_all_projects:
        projects = get_internal_projects()
    else:
        projects = [get_project_and_check_permissions(project_guid, request.user)]

    individual_samples = get_loaded_before_date_project_individual_samples(
        projects, request.GET.get('loadedBefore') or datetime.now().strftime('%Y-%m-%d'))
    subject_rows, sample_rows, family_rows, discovery_rows = parse_anvil_metadata(
        individual_samples, request.user, include_collaborator=True, omit_airtable=omit_airtable,
        family_values={'MME': Case(When(individual__matchmakersubmission__isnull=True, then=Value('N')), default=Value('Y'))}
    )
    family_rows_by_id = {row['family_id']: row for row in family_rows}

    rows_by_subject_family_id = {(row['subject_id'], row['family_guid']): row for row in subject_rows}
    for row in sample_rows:
        rows_by_subject_family_id[(row['subject_id'], row['family_guid'])].update(row)

    for rows in discovery_rows:
        for i, row in enumerate(rows):
            if row:
                parsed_row = {k: row[k] for k in DISCOVERY_TABLE_CORE_COLUMNS}
                parsed_row.update({
                    '{}-{}'.format(k, i + 1): row[k]
                    for k in DISCOVERY_TABLE_VARIANT_COLUMNS + ['novel_mendelian_gene', 'phenotype_class'] if row.get(k)
                })
                rows_by_subject_family_id[(row['subject_id'], row['family_guid'])].update(parsed_row)

    rows = list(rows_by_subject_family_id.values())
    all_features = set()
    for row in rows:
        row.update(family_rows_by_id[row['family_id']])
        if row['ancestry_detail']:
            row['ancestry'] = row['ancestry_detail']
        all_features.update(row['hpo_present'].split('|'))
        all_features.update(row['hpo_absent'].split('|'))

    hpo_name_map = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_features)}
    for row in rows:
        for hpo_key in ['hpo_present', 'hpo_absent']:
            if row[hpo_key]:
                row[hpo_key] = '|'.join(['{} ({})'.format(feature_id, hpo_name_map.get(feature_id, '')) for feature_id in row[hpo_key].split('|')])

    return create_json_response({'rows': rows})
