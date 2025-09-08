from collections import defaultdict
from datetime import datetime
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied
from django.core.mail.message import EmailMessage
from django.contrib.auth.models import User
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Coalesce, Concat, JSONObject, NullIf
import json

from clickhouse_search.search import get_clickhouse_keys_for_gene, get_all_clickhouse_keys_for_gene
from matchmaker.matchmaker_utils import get_mme_gene_phenotype_ids_for_submissions, parse_mme_features, \
    get_mme_metrics, get_hpo_terms_by_id
from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology, GeneInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38
from seqr.models import Project, Family, Individual, VariantTagType, SavedVariant, FamilyAnalysedBy, Sample
from seqr.views.utils.airtable_utils import AirtableSession
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.utils.communication_utils import safe_post_to_slack, set_email_message_stream
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.json_utils import create_json_response
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions, get_json_for_saved_variants,\
    add_individual_hpo_details, INDIVIDUAL_DISPLAY_NAME_EXPR, AIP_TAG_TYPE
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required, get_project_and_check_permissions, get_internal_projects
from seqr.views.utils.anvil_metadata_utils import parse_anvil_metadata, anvil_export_airtable_fields, FAMILY_ROW_TYPE, SUBJECT_ROW_TYPE, DISCOVERY_ROW_TYPE
from seqr.views.utils.variant_utils import get_variants_response, bulk_create_tagged_variants, DISCOVERY_CATEGORY
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, VLM_SEND_EMAIL

logger = SeqrLogger(__name__)

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
        additional_values={'genomeVersion': F('family__project__genome_version')},
    )

    response = {
        'submissions': list(submissions_by_guid.values()),
        'genesById': genes_by_id,
        'savedVariantsByGuid': {s['variantGuid']: {**s, 'chrom': get_chrom_pos(s['xpos'])[0] , 'pos': get_chrom_pos(s['xpos'])[1]} for s in saved_variants},
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
    is_all_tags = tag == 'ALL'
    if is_all_tags:
        saved_variant_models = SavedVariant.objects.exclude(varianttag=None)
    else:
        tags = tag.split(';')
        tag_types = VariantTagType.objects.filter(name__in=tags, project__isnull=True)
        saved_variant_models = SavedVariant.objects.filter(
            varianttag__variant_tag_type__category=DISCOVERY_CATEGORY, varianttag__variant_tag_type__project__isnull=True,
        ).distinct() if DISCOVERY_CATEGORY in tags else SavedVariant.objects.all()
        for tt in tag_types:
            saved_variant_models = saved_variant_models.filter(varianttag__variant_tag_type=tt).distinct()

    saved_variant_models = saved_variant_models.filter(family__project__guid__in=get_project_guids_user_can_view(request.user))

    if gene:
        gene_filter = Q(saved_variant_json__transcripts__has_key=gene) | backend_specific_call(
            lambda *args: Q(),
            _saved_variant_with_clickhouse_gene_q,
        )(saved_variant_models, gene, is_all_tags)
        saved_variant_models = saved_variant_models.filter(gene_filter)
    elif saved_variant_models.count() > MAX_SAVED_VARIANTS:
        return create_json_response({'error': 'Select a gene to filter variants'}, status=400)

    response_json = get_variants_response(
        request, saved_variant_models, add_all_context=True, include_igv=False, add_locus_list_detail=True,
        include_individual_gene_scores=False, include_project_name=True,
    )

    return create_json_response(response_json)


def _saved_variant_with_clickhouse_gene_q(saved_variant_models, gene_id, is_all_tags):
    key_qs = []
    if is_all_tags:
        gene_model = GeneInfo.objects.get(gene_id=gene_id)
        for genome_version in [GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38]:
            gene_keys = get_all_clickhouse_keys_for_gene(gene_model, genome_version)
            if gene_keys:
                key_qs.append(
                    Q(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, family__project__genome_version=genome_version, key__in=gene_keys)
                )
        saved_variant_models = saved_variant_models.exclude(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)

    search_type_keys = saved_variant_models.filter(key__isnull=False).values(
        'dataset_type', genome_version=F('family__project__genome_version'),
    ).annotate(keys=ArrayAgg('key', distinct=True))
    for agg in search_type_keys:
        gene_keys = get_clickhouse_keys_for_gene(gene_id, **agg)
        if gene_keys:
            q = Q(dataset_type=agg['dataset_type'], family__project__genome_version=agg['genome_version'], key__in=gene_keys)
            key_qs.append(q)

    if not key_qs:
        return Q()
    has_key_q = key_qs[0]
    for q in key_qs[1:]:
        has_key_q |= q
    return has_key_q


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
def bulk_update_family_external_analysis(request):
    request_json = json.loads(request.body)
    data_type = request_json['dataType']
    family_upload_data = load_uploaded_file(request_json['familiesFile']['uploadedFileId'])

    if data_type == AIP_TAG_TYPE:
        return _load_aip_data(family_upload_data, request.user)

    header = [col.split()[0].lower() for col in family_upload_data[0]]
    if not ('project' in header and 'family' in header):
        return create_json_response({'error': 'Project and Family columns are required'}, status=400)
    requested_families = {(row[header.index('project')], row[header.index('family')]) for row in family_upload_data[1:]}

    family_db_id_lookup = {
        (f['project__name'], f['family_id']): f['id'] for f in Family.objects.annotate(
            project_family=Concat('project__name', 'family_id', output_field=CharField())
        ).filter(
            project_family__in=[f'{project}{family}' for project, family in requested_families],
            project__guid__in=get_project_guids_user_can_view(request.user),
        ).values('id', 'family_id', 'project__name')
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
    FamilyAnalysedBy.bulk_create(request.user, analysed_by_models)

    return create_json_response({
        'warnings': warnings,
        'info': [f'Updated "analysed by" for {len(analysed_by_models)} families'],
    })


def _load_aip_data(data: dict, user: User):
    category_map = data['metadata']['categories']
    projects = data['metadata'].get('projects')
    results = data['results']

    if not projects:
        raise ErrorsWarningsException(['No projects specified in the metadata'])

    family_id_map = defaultdict(list)
    for individual_id, family_id in Individual.objects.filter(
        family__project__in=get_internal_projects().filter(name__in=projects), individual_id__in=results.keys(),
    ).values_list('individual_id', 'family_id'):
        family_id_map[individual_id].append(family_id)
    errors = []
    missing_individuals = set(results.keys()) - set(family_id_map.keys())
    if missing_individuals:
        errors.append(f'Unable to find the following individuals: {", ".join(sorted(missing_individuals))}')
    multi_family_individuals = {individual_id for individual_id, families in family_id_map.items() if len(families) > 1}
    if multi_family_individuals:
        errors.append(f'The following individuals are found in multiple families: {", ".join(sorted(multi_family_individuals))}')
    if errors:
        raise ErrorsWarningsException(errors)

    family_variant_data = {}
    for family_id, variant_pred in results.items():
        family_variant_data.update({
            (family_id_map[family_id][0], variant_id): pred for variant_id, pred in variant_pred.items()
        })

    today = datetime.now().strftime('%Y-%m-%d')
    num_new, num_updated = bulk_create_tagged_variants(
        family_variant_data, tag_name=AIP_TAG_TYPE, user=user, load_new_variant_data=True,
        get_metadata=lambda pred:  {category: {'name': category_map[category], 'date': today} for category in pred['categories']},
    )

    summary_message = f'Loaded {num_new} new and {num_updated} updated AIP tags for {len(family_id_map)} families'
    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
        f'{summary_message}:\n```{", ".join(sorted(family_id_map.keys()))}```',
    )

    return create_json_response({
        'info': [summary_message],
    })


ALL_PROJECTS = 'all'
GREGOR_CATEGORY = 'gregor'


def _get_metadata_projects(request, project_guid):
    is_analyst = user_is_analyst(request.user)
    is_all_projects = project_guid == ALL_PROJECTS
    include_airtable = 'true' in request.GET.get('includeAirtable', '') and AirtableSession.is_airtable_enabled() and is_analyst and not is_all_projects
    if is_all_projects:
        projects = get_internal_projects() if is_analyst else Project.objects.filter(
            guid__in=get_project_guids_user_can_view(request.user))
    elif project_guid == GREGOR_CATEGORY:
        if not is_analyst:
            raise PermissionDenied()
        projects = Project.objects.filter(projectcategory__name__iexact=GREGOR_CATEGORY)
    else:
        projects = [get_project_and_check_permissions(project_guid, request.user)]
    return projects, include_airtable


@login_and_policies_required
def individual_metadata(request, project_guid):
    projects, include_airtable = _get_metadata_projects(request, project_guid)

    family_rows_by_id = {}
    rows_by_subject_family_id = defaultdict(dict)
    collaborator_map = {}
    all_features = set()

    def _add_row(row, family_id, row_type):
        if row_type == FAMILY_ROW_TYPE:
            family_rows_by_id[family_id] = row
        elif row_type == DISCOVERY_ROW_TYPE:
            for i, discovery_row in enumerate(row):
                participant_id = discovery_row.pop('participant_id')
                parsed_row = {'{}-{}'.format(k, i + 1): v for k, v in discovery_row.items() if k not in {'allele_balance_or_heteroplasmy_percentage', 'variant_type'}}
                parsed_row['num_saved_variants'] = len(row)
                rows_by_subject_family_id[(participant_id, family_id)].update(parsed_row)
        elif row_type == SUBJECT_ROW_TYPE:
            row_key = (row['participant_id'], family_id)
            collaborator = row.pop('Collaborator', None)
            if collaborator:
                collaborator_map[row_key] = collaborator
            is_additional_affected = row.pop('is_additional_affected')
            if is_additional_affected:
                family_rows_by_id[family_id]['family_history'] = 'Yes'
            race = row.pop('reported_race')
            ancestry_detail = row.pop('ancestry_detail')
            ethnicity = row.pop('reported_ethnicity')
            row['ancestry'] = ethnicity or ancestry_detail or race
            row.update({
                'hpo_present': [feature['id'] for feature in row.pop('features') or []],
                'hpo_absent': [feature['id'] for feature in row.pop('absent_features') or []],
            })
            all_features.update(row['hpo_present'])
            all_features.update(row['hpo_absent'])
            rows_by_subject_family_id[row_key].update(row)
        else:
            row.pop('sample_id')
            rows_by_subject_family_id[(row['participant_id'], family_id)].update(row)

    parse_anvil_metadata(
        projects, request.user, _add_row, max_loaded_date=request.GET.get('loadedBefore'),
        include_family_sample_metadata=True,
        omit_airtable=not include_airtable,
        mme_value=Value('Yes'),
        get_additional_individual_fields=lambda individual, airtable_metadata, has_dbgap_submission, maternal_ids, paternal_ids: {
            'Collaborator': (airtable_metadata or {}).get('Collaborator'),
            'individual_guid': individual.guid,
            'disorders': individual.disorders,
            'filter_flags': json.dumps(individual.filter_flags) if individual.filter_flags else '',
            'paternal_guid': paternal_ids[1],
            'maternal_guid': maternal_ids[1],
            'is_additional_affected': individual.affected == Individual.AFFECTED_STATUS_AFFECTED and individual.proband_relationship != Individual.SELF_RELATIONSHIP,
            **anvil_export_airtable_fields(airtable_metadata, has_dbgap_submission),
        },
    )

    if collaborator_map:
        collaborator_name_map = _get_airtable_collaborator_names(request.user, collaborator_map.values())
        for row_key, collaborator_id in collaborator_map.items():
            rows_by_subject_family_id[row_key]['sample_provider'] = collaborator_name_map.get(collaborator_id)

    hpo_name_map = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_features)}
    for row_key, row in rows_by_subject_family_id.items():
        row.update({k: v for k, v in family_rows_by_id[row_key[1]].items() if k not in row})
        row['num_saved_variants'] = row.get('num_saved_variants', 0)
        for hpo_key in ['hpo_present', 'hpo_absent']:
            features = row.pop(hpo_key)
            if features:
                row[hpo_key] = '|'.join(['{} ({})'.format(feature_id, hpo_name_map.get(feature_id, '')) for feature_id in features])

    return create_json_response({'rows': list(rows_by_subject_family_id.values())})


def _get_airtable_collaborator_names(user, collaborator_ids):
    collaborator_map = AirtableSession(user).fetch_records(
        'Collaborator', fields=['CollaboratorID'], or_filters={'RECORD_ID()': collaborator_ids}
    )
    return {
        collaborator_id: collaborator_map.get(collaborator_id, {}).get('CollaboratorID')
        for collaborator_id in collaborator_ids
    }


@login_and_policies_required
def send_vlm_email(request):
    request_json = json.loads(request.body)
    email_message = EmailMessage(
        subject=request_json['subject'],
        body=request_json['body'],
        bcc=[s.strip() for s in request_json['to'].split(',')],
        cc=[request.user.email],
        reply_to=[request.user.email],
        to=[VLM_SEND_EMAIL],
        from_email=VLM_SEND_EMAIL,
    )
    set_email_message_stream(email_message, 'vlm')

    try:
        email_message.send()
    except Exception as e:
        logger.error(f'VLM Email Error: {e}', request.user, detail=request_json)

    return create_json_response({'success': True})
