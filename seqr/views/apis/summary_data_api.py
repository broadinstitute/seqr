from collections import defaultdict
from datetime import datetime
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Coalesce, Concat, JSONObject, NullIf
import json
from random import randint
from typing import Optional

from matchmaker.matchmaker_utils import get_mme_gene_phenotype_ids_for_submissions, parse_mme_features, \
    get_mme_metrics, get_hpo_terms_by_id
from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology
from seqr.models import Project, Family, Individual, VariantTag, VariantTagType, SavedVariant, FamilyAnalysedBy
from seqr.views.utils.airtable_utils import AirtableSession
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.gene_utils import get_genes
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import get_variants_for_variant_ids, InvalidSearchException
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions, get_json_for_saved_variants,\
    add_individual_hpo_details, INDIVIDUAL_DISPLAY_NAME_EXPR, AIP_TAG_TYPES
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required, get_project_and_check_permissions, get_internal_projects
from seqr.views.utils.anvil_metadata_utils import parse_anvil_metadata, FAMILY_ROW_TYPE, SUBJECT_ROW_TYPE, SAMPLE_ROW_TYPE, DISCOVERY_ROW_TYPE
from seqr.views.utils.variant_utils import get_variants_response, bulk_create_tagged_variants, DISCOVERY_CATEGORY
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

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
        saved_variant_models = SavedVariant.objects.filter(
            varianttag__variant_tag_type__category=DISCOVERY_CATEGORY, varianttag__variant_tag_type__project__isnull=True,
        ).distinct() if DISCOVERY_CATEGORY in tags else SavedVariant.objects.all()
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


AIP_INGEST_FULL_REPORT_DESC = 'CPG: Full AIP report'


@analyst_required
def bulk_update_family_external_analysis(request):
    request_json = json.loads(request.body)
    data_type = request_json['dataType']
    family_upload_data = load_uploaded_file(request_json['familiesFile']['uploadedFileId'])

    if data_type in AIP_TAG_TYPES:
        return _load_aip_data(family_upload_data, request.user, data_type)

    if data_type == AIP_INGEST_FULL_REPORT_DESC:
        return _load_aip_full_report_data(family_upload_data, request.user)

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
    for ab in analysed_by_models:
        ab.guid = f'FAB{randint(10**5, 10**6)}_{ab}'[:FamilyAnalysedBy.MAX_GUID_SIZE] # nosec
    FamilyAnalysedBy.bulk_create(request.user, analysed_by_models)

    return create_json_response({
        'warnings': warnings,
        'info': [f'Updated "analysed by" for {len(analysed_by_models)} families'],
    })


def _load_aip_data(data: dict, user: User, aip_tag_name: str):
    category_map = data['metadata']['categories']
    results = data['results']

    family_id_map = dict(Individual.objects.filter(
        family__project__in=get_internal_projects(), individual_id__in=results.keys(),
    ).values_list('individual_id', 'family_id'))
    missing_individuals = set(results.keys()) - set(family_id_map.keys())
    if missing_individuals:
        raise ErrorsWarningsException([f'Unable to find the following individuals: {", ".join(sorted(missing_individuals))}'])

    family_variant_data = {}
    for family_id, variant_pred in results.items():
        family_variant_data.update({
            (family_id_map[family_id], variant_id): pred for variant_id, pred in variant_pred.items()
        })
        all_variant_ids.update(variant_pred.keys())

    saved_variant_map = {
        (v.family_id, v.variant_id): v
        for v in SavedVariant.objects.filter(family_id__in=family_id_map.values(), variant_id__in=all_variant_ids)
    }

    new_variants = set(family_variant_data.keys()) - set(saved_variant_map.keys())
    if new_variants:
        saved_variant_map.update(_search_new_saved_variants(new_variants, user))

    aip_tag_type = VariantTagType.objects.get(name=aip_tag_name, project=None)
    existing_tags = {
        tuple(t.saved_variant_ids): t for t in VariantTag.objects.filter(
            variant_tag_type=aip_tag_type, saved_variants__in=saved_variant_map.values(),
        ).annotate(saved_variant_ids=ArrayAgg('saved_variants__id', ordering='id'))
    }

    today = datetime.now().strftime('%Y-%m-%d')
    update_tags = []
    num_new = 0
    for key, pred in family_variant_data.items():
        metadata = {'categories':{category: {'name': category_map[category], 'date': today} for category in pred['categories']}}
        updated_tag = _set_aip_tags(
            key, metadata, pred['support_vars'], saved_variant_map, existing_tags, aip_tag_type, user,
        )
        if updated_tag:
            update_tags.append(updated_tag)
        else:
            num_new += 1

    summary_message = f'Loaded {num_new} new and {num_updated} updated AIP tags for {len(family_id_map)} families'
    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
        f'{summary_message}:\n```{", ".join(sorted(family_id_map.keys()))}```',
    )

    return create_json_response({
        'info': [summary_message],
    })


FamilyVariantKey = tuple[int, str]


def _search_new_saved_variants(family_variant_ids: list[FamilyVariantKey], user: User, warnings: Optional[list[str]] = None):
    """
    Retrieve all variants from the search backend and create SavedVariants if they do not already exist.

    The optional argument "warnings" is a list that will be populated with any errors resulting
    from expected families or variants not found in the search backend.
    """
    family_ids = set()
    variant_families = defaultdict(list)
    for family_id, variant_id in family_variant_ids:
        family_ids.add(family_id)
        variant_families[variant_id].append(family_id)
    families_by_id = {f.id: f for f in Family.objects.filter(id__in=family_ids)}

    try:
        search_variants_by_id = {
            v['variantId']: v for v in get_variants_for_variant_ids(
                families=families_by_id.values(), variant_ids=variant_families.keys(), user=user,
            )
        }

    except InvalidSearchException as e:
        # If all new variants are from families that are not in the search backend
        if warnings is None:
            raise e

        search_variants_by_id = {}
        warnings.append(str(e))

    new_variants = []
    missing = defaultdict(list)
    for variant_id, family_ids in variant_families.items():
        variant = search_variants_by_id.get(variant_id) or {'familyGuids': []}
        for family_id in family_ids:
            family = families_by_id[family_id]
            if family.guid in variant['familyGuids']:
                new_variants[(family_id, variant_id)] = variant
            else:
                missing[family.family_id].append(variant_id)

    if missing:
        missing_summary = [f'{family} ({", ".join(sorted(variant_ids))})' for family, variant_ids in missing.items()]

        if warnings is None:
            raise ErrorsWarningsException([
                f"Unable to find the following family's AIP variants in the search backend: {', '.join(missing_summary)}",
            ])
        warnings.append(f'Unable to find the following family\'s variants in the search backend: {missing_summary}')

    saved_variants = SavedVariant.bulk_create(user, new_variants)
    return {(v.family_id, v.variant_id): v for v in saved_variants}


def _set_aip_tags(key: FamilyVariantKey, metadata: dict[str, dict], support_var_ids: list[str],
                  saved_variant_map: dict[FamilyVariantKey, SavedVariant], existing_tags: dict[tuple[int, ...], VariantTag],
                  aip_tag_type: VariantTagType, user: User):
    variant = saved_variant_map[key]
    existing_tag = existing_tags.get(tuple([variant.id]))
    updated_tag = None
    if existing_tag:
        existing_metadata = json.loads(existing_tag.metadata or '{}')

        # If existing metadata holds catagories at the top level, move them to the categories field.
        if 'categories' not in existing_metadata:
            existing_metadata['categories'] = {k: v for k, v in existing_metadata.items() if k != 'removed'}

        metadata['categories'] = {k: existing_metadata['categories'].get(k, v) for k, v in metadata['categories'].items()}
        removed = {k: v for k, v in existing_metadata.get('removed', {}).items() if k not in metadata['categories']}
        removed.update({k: v for k, v in existing_metadata['categories'].items() if k not in metadata['categories']})
        if removed:
            metadata['removed'] = removed
        existing_tag.metadata = json.dumps(metadata)
        updated_tag = existing_tag
    else:
        tag = create_model_from_json(
            VariantTag, {'variant_tag_type': aip_tag_type, 'metadata': json.dumps(metadata)}, user)
        tag.saved_variants.add(variant)

    variant_genes = set(variant.saved_variant_json['transcripts'].keys())
    support_vars = []
    for support_id in support_var_ids:
        if (key[0], support_id) in saved_variant_map:
            support_v = saved_variant_map[(key[0], support_id)]
            if variant_genes.intersection(set(support_v.saved_variant_json['transcripts'].keys())):
                support_vars.append(support_v)
    if support_vars:
        variants = [variant] + support_vars
        variant_id_key = tuple(sorted([v.id for v in variants]))
        if variant_id_key not in existing_tags:
            tag = create_model_from_json(VariantTag, {'variant_tag_type': aip_tag_type}, user)
            tag.saved_variants.set(variants)
            existing_tags[variant_id_key] = True

    return updated_tag


ALL_PROJECTS = 'all'
GREGOR_CATEGORY = 'gregor'


def _get_metadata_projects(request, project_guid):
    is_analyst = user_is_analyst(request.user)
    is_all_projects = project_guid == ALL_PROJECTS
    include_airtable = 'true' in request.GET.get('includeAirtable', '') and is_analyst and not is_all_projects
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
                del discovery_row['gene_ids']
                participant_id = discovery_row.pop('participant_id')
                parsed_row = {'{}-{}'.format(k, i + 1): v for k, v in discovery_row.items()}
                parsed_row['num_saved_variants'] = len(row)
                rows_by_subject_family_id[(participant_id, family_id)].update(parsed_row)
        else:
            row_key = (row['participant_id'], family_id)
            collaborator = row.pop('Collaborator', None)
            if collaborator:
                collaborator_map[row_key] = collaborator
            if row_type == SUBJECT_ROW_TYPE:
                race = row.pop('reported_race')
                ancestry_detail = row.pop('ancestry_detail')
                ethnicity = row.pop('reported_ethnicity')
                row['ancestry'] = ethnicity or ancestry_detail or race
            if 'features' in row:
                row.update({
                    'hpo_present': [feature['id'] for feature in row.pop('features') or []],
                    'hpo_absent': [feature['id'] for feature in row.pop('absent_features') or []],
                })
                all_features.update(row['hpo_present'])
                all_features.update(row['hpo_absent'])
            rows_by_subject_family_id[row_key].update(row)

    # parse_anvil_metadata(
    #     projects, request.user, _add_row, max_loaded_date=request.GET.get('loadedBefore'),
    #     include_metadata=True,
    #     omit_airtable=not include_airtable,
    #     get_additional_individual_fields=lambda individual, airtable_metadata: {
    #         'Collaborator': (airtable_metadata or {}).get('Collaborator'),
    #         'individual_guid': individual.guid,
    #         'disorders': individual.disorders,
    #         'filter_flags': json.dumps(individual.filter_flags) if individual.filter_flags else '',
    #     },
    # )

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
def family_metadata(request, project_guid):
    projects, _ = _get_metadata_projects(request, project_guid)

    families_by_id = {}
    family_individuals = defaultdict(dict)

    def _add_row(row, family_id, row_type):
        if row_type == FAMILY_ROW_TYPE:
            families_by_id[family_id] = row
        elif row_type == SUBJECT_ROW_TYPE:
            family_individuals[family_id][row['participant_id']] = row
        elif row_type == SAMPLE_ROW_TYPE:
            family_individuals[family_id][row['participant_id']].update(row)
        elif row_type == DISCOVERY_ROW_TYPE:
            family = families_by_id[family_id]
            if 'inheritance_models' not in family:
                family.update({'genes': set(), 'inheritance_models': set()})
            family['genes'].update({v.get('gene') or v.get('sv_name') or v.get('gene_id') or '' for v in row})
            family['inheritance_models'].update({v['variant_inheritance'] for v in row})

    parse_anvil_metadata(
        projects, user=request.user, add_row=_add_row, omit_airtable=True, include_metadata=True, include_no_individual_families=True)

    for family_id, f in families_by_id.items():
        individuals_by_id = family_individuals[family_id]
        proband = next((i for i in individuals_by_id.values() if i['proband_relationship'] == 'Self'), None)
        individuals_ids = set(individuals_by_id.keys())
        known_ids = {}
        if proband:
            known_ids = {
                'proband_id': proband['participant_id'],
                'paternal_id': proband['paternal_id'],
                'maternal_id': proband['maternal_id'],
            }
            f.update(known_ids)
            individuals_ids -= set(known_ids.values())

        sorted_samples = sorted(individuals_by_id.values(), key=lambda x: x.get('date_data_generation', ''))
        earliest_sample = next((s for s in [proband or {}] + sorted_samples if s.get('date_data_generation')), {})

        inheritance_models = f.pop('inheritance_models', [])
        f.update({
            'individual_count': len(individuals_by_id),
            'other_individual_ids':  '; '.join(sorted(individuals_ids)),
            'family_structure': _get_family_structure(len(individuals_by_id), sum(1 for id in known_ids.values() if id)),
            'data_type': earliest_sample.get('data_type'),
            'date_data_generation': earliest_sample.get('date_data_generation'),
            'genes': '; '.join(sorted(f.get('genes', []))),
            'actual_inheritance': 'unknown' if inheritance_models == {'unknown'} else ';'.join(
                sorted([i for i in inheritance_models if i != 'unknown'])),
        })

    return create_json_response({'rows': list(families_by_id.values())})


FAMILY_STRUCTURES = {
    1: 'singleton',
    2: 'duo',
    3: 'trio',
    4: 'quad',
}


def _get_family_structure(num_individuals, num_known_individuals):
    if (num_individuals and num_known_individuals == num_individuals) or (
            num_known_individuals in {0, 3} and num_individuals == num_known_individuals + 1):
        return FAMILY_STRUCTURES[num_individuals]
    return 'other'


@login_and_policies_required
def variant_metadata(request, project_guid):
    projects, _ = _get_metadata_projects(request, project_guid)

    individuals = Individual.objects.filter(
        family__project__in=projects, family__savedvariant__varianttag__variant_tag_type__category=DISCOVERY_CATEGORY,
    ).distinct().annotate(
        data_types=ArrayAgg('sample__sample_type', distinct=True, filter=Q(sample__isnull=False))
    )

    families_by_id = {}
    participant_mme = {}
    variant_rows = []

    def _add_row(row, family_id, row_type):
        if row_type == FAMILY_ROW_TYPE:
            families_by_id[family_id] = row
        elif row_type == SUBJECT_ROW_TYPE:
            participant_mme[row['participant_id']] = row.get('MME', {})
        elif row_type == DISCOVERY_ROW_TYPE:
            family = families_by_id[family_id]
            for variant in row:
                del variant['gene_ids']
                variant_rows.append({
                    'MME': variant.pop('variantId') in participant_mme[variant['participant_id']].get('variant_ids', []),
                    'phenotype_contribution': 'Full',
                    **family,
                    **variant,
                })

    parse_anvil_metadata(
        projects,
        user=request.user,
        individual_samples={i: None for i in individuals},
        individual_data_types={i.individual_id: i.data_types for i in individuals},
        add_row=_add_row,
        variant_json_fields=['clinvar', 'variantId'],
        mme_values={'variant_ids': ArrayAgg('matchmakersubmissiongenes__saved_variant__saved_variant_json__variantId')},
        include_metadata=True,
        include_mondo=True,
        omit_airtable=True,
        proband_only_variants=True,
        include_parent_mnvs=True,
    )

    return create_json_response({'rows': variant_rows})


def _load_aip_full_report_data(data: dict, user: User):
    """
        Version of _load_aip_data that ingests a full AIP report rather than the
        cut down "seqr" format.

        - Adds both the AIP-permissive and AIP-restrictive tags
          depending on the presence of HPO matches in the variant.
        - Adds the First Seen metadata field to the tags.

    """
    category_map = data['metadata']['categories']
    results = data['results']
    warnings = []

    # This endpoint does not let us specify the project, so we are going to add a list
    # of target projects into the report.
    projects = Project.objects.filter(guid__in=data['metadata']['projects'])
    if not projects:
        raise ErrorsWarningsException([
            f"Unable to find projects with GUIDs = {data['metadata']['projects']}"
        ])

    # Get a map of the family_ids associated with each individual in the report.
    # A given individual may be in multiple projects.
    individual_ids = [individual['metadata']['ext_id'] for individual in results.values()]
    family_id_map = defaultdict(list)
    all_family_ids = set()
    for individual_id, family_id in Individual.objects.filter(
        family__project__in=projects, individual_id__in=individual_ids,
    ).values_list('individual_id', 'family_id'):
        family_id_map[individual_id].append(family_id)
        all_family_ids.add(family_id)

    missing_individuals = set(individual_ids) - set(family_id_map.keys())
    if missing_individuals:
        raise ErrorsWarningsException([
            f'Unable to find the following individuals: {", ".join(sorted(missing_individuals))} '
            f'when searching in the project/s: {", ".join(projects.values_list("name", flat=True))}',
        ])

    # Make a dict of (family_id, variant_id) -> AIP prediction for variant.
    # Adds the variant multiple times if the family is in multiple projects.
    all_variant_ids = set()
    family_variant_data = {}
    for sg_id, individual_aip_results in results.items():
        individual_id = results[sg_id]['metadata']['ext_id']
        family_ids = family_id_map[individual_id]
        for family_id in family_ids:
            for variant_result in individual_aip_results['variants']:
                variant_id = variant_result['var_data']['info']['seqr_link']
                family_variant_data[(family_id, variant_id)] = variant_result
                all_variant_ids.add(variant_id)

    # Get a map of the saved variants that are already in the database.
    saved_variant_map = {
        (v.family_id, v.variant_id): v
        for v in SavedVariant.objects.filter(family_id__in=all_family_ids, variant_id__in=all_variant_ids)
    }

    # If the variant has not been "saved" before, find it in the search backend and save it.
    new_variants = set(family_variant_data.keys()) - set(saved_variant_map.keys())
    if new_variants:
        new_variants_from_search = _search_new_saved_variants(new_variants, user, warnings)
        saved_variant_map.update(new_variants_from_search)

    # Add the aip_permissive tag to all variants
    aip_tag_type = VariantTagType.objects.get(name='AIP-permissive', project=None)
    num_new, num_updated = _cpg_add_aip_tags_to_saved_variants(aip_tag_type, saved_variant_map, family_variant_data, category_map, user, restrictive=False)

    # Add the aip_restrictive tag to qualifying variants
    aip_restrictive_tag_type = VariantTagType.objects.get(name='AIP-restrictive', project=None)
    num_new_restrictive, num_updated_restrictive = _cpg_add_aip_tags_to_saved_variants(aip_restrictive_tag_type, saved_variant_map, family_variant_data, category_map, user, restrictive=True)

    summary_message = f'Loaded {num_new} new ({num_new_restrictive} restrictive) and {num_updated} updated ({num_updated_restrictive} restrictive) AIP tags for {len(family_id_map)} families'
    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
        f'{summary_message}:\n```{", ".join(sorted(family_id_map.keys()))}```',
    )

    return create_json_response({
        'info': [summary_message],
        'warnings': warnings,
    })


def _cpg_add_aip_tags_to_saved_variants(aip_tag_type, saved_variant_map, family_variant_data, category_map, user, restrictive=False):
    existing_tags = {
        tuple(t.saved_variant_ids): t for t in VariantTag.objects.filter(
            variant_tag_type=aip_tag_type, saved_variants__in=saved_variant_map.values(),
        ).annotate(saved_variant_ids=ArrayAgg('saved_variants__id', ordering='id'))
    }

    # Add/update a metadata field on each tags containing the AIP results that will be displayed.
    today = datetime.now().strftime('%Y-%m-%d')
    update_tags = []
    num_new = 0

    for key, variant_result in family_variant_data.items():
        if restrictive:
            # Skip if the variant if if does not have a HPO match.
            if not any(hpo_match for hpo_match in variant_result['panels'].values()):
                continue

        # Skip if the variant is not in the saved map.
        if key not in saved_variant_map:
            continue

        # Copy selected metadata fields from the AIP results to the tag metadata.
        metadata = {}
        for k in ['flags', 'independent', 'labels', 'panels', 'phenotypes', 'reasons', 'support_vars']:
            metadata[k] = variant_result[k]

        if restrictive:
            metadata['first_tagged'] = variant_result.get('first_seen_restrictive', variant_result['first_seen'])
        else:
            metadata['first_tagged'] = variant_result['first_seen']

        # Add the categories using the date of ingest as the date.
        metadata['categories'] = {category: {'name': category_map[category], 'date': today} for category in variant_result['categories']}

        updated_tag = _set_aip_tags(
            key, metadata, variant_result['support_vars'], saved_variant_map, existing_tags, aip_tag_type, user,
        )
        if updated_tag:
            update_tags.append(updated_tag)
        else:
            num_new += 1

    VariantTag.bulk_update_models(user, update_tags, ['metadata'])

    return num_new, len(update_tags)
