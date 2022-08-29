"""API that generates auto-complete suggestions for the search bar in the header of seqr pages"""
from django.db.models import F, Q, Case, When, Value, ExpressionWrapper, BooleanField, CharField
from django.db.models.functions import Cast, Coalesce, Concat, Left, Length, NullIf, Replace
from django.views.decorators.http import require_GET

from reference_data.models import Omim, HumanPhenotypeOntology
from seqr.utils.gene_utils import get_queried_genes
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from seqr.views.utils.permissions_utils import get_project_guids_user_can_view, login_and_policies_required
from seqr.models import Project, Family, Individual, AnalysisGroup, ProjectCategory
from settings import ANALYST_PROJECT_CATEGORY


MAX_RESULTS_PER_CATEGORY = 8
MAX_STRING_LENGTH = 100

FUZZY_MATCH_CHARS = ['-', '_', '.']


def _get_matching_objects(query, project_guids, object_cls, core_fields, href_expression, description_content=None,
                          project_field=None, select_related_project=True, exclude_criteria=None):
    if project_field:
        matching_objects = getattr(object_cls, 'objects')
        matching_objects = matching_objects.filter(Q(**{'{}__guid__in'.format(project_field): project_guids}))
        if select_related_project:
            matching_objects = matching_objects.select_related(project_field)
    else:
        matching_objects = object_cls.objects.filter(guid__in=project_guids)

    if exclude_criteria:
        matching_objects = matching_objects.exclude(**exclude_criteria)

    object_filter = Q()
    for field in core_fields:
        object_filter |= Q(**{'{}__icontains'.format(field): query})

    sort_order = [Case(When(title__istartswith=query, then=False), default=True), Length('title')]

    fuzzy_query = query
    if any(c in query for c in FUZZY_MATCH_CHARS):
        fuzzy_annotations = {f'fuzzy_{field}': Cast(field, output_field=CharField()) for field in core_fields}
        matching_objects = matching_objects.annotate(**fuzzy_annotations)
        for c in FUZZY_MATCH_CHARS:
            fuzzy_query = fuzzy_query.replace(c, '')
            matching_objects = matching_objects.annotate(**{
                field: Replace(field, Value(c)) for field in fuzzy_annotations.keys()})

        startswith_fuzzy_q = Q()
        for field in fuzzy_annotations.keys():
            object_filter |= Q(**{'{}__icontains'.format(field): fuzzy_query})
            startswith_fuzzy_q |= Q(**{'{}__istartswith'.format(field): fuzzy_query})

        sort_order = [
            sort_order[0],
            Case(When(title__icontains=query, then=False), default=True),
            Case(When(startswith_fuzzy_q, then=False), default=True),
            sort_order[1],
        ]

    results = matching_objects.filter(object_filter).distinct().values(
        key=F('guid'),
        title=Left(
            Coalesce(*[NullIf(f, Value('')) for f in core_fields]) if len(core_fields) > 1 else core_fields[0],
            MAX_STRING_LENGTH,
        ),
        result_description=Concat(Value('('), *description_content, Value(')')) if description_content else Value(''),
        href=href_expression,
    ).values(
        # secondary call to values to prevent field collision for "description"
        'key', 'title', 'href', description=F('result_description'),
    ).order_by(*sort_order)[:MAX_RESULTS_PER_CATEGORY]

    return list(results)


def _get_matching_projects(query, project_guids):
    return _get_matching_objects(
        query, project_guids, Project,
        core_fields=['name'],
        href_expression=Concat(Value('/project/'), 'guid', Value('/project_page')),
    )


def _get_matching_families(query, project_guids):
    return _get_matching_objects(
        query, project_guids, Family,
        core_fields=['display_name', 'family_id'],
        href_expression=Concat(Value('/project/'), 'project__guid', Value('/family_page/'), 'guid'),
        description_content=[Cast('project__name', output_field=CharField())],
        project_field='project')


def _get_matching_analysis_groups(query, project_guids):
    return _get_matching_objects(
        query, project_guids, AnalysisGroup,
        core_fields=['name'],
        href_expression=Concat(Value('/project/'), 'project__guid', Value('/analysis_group/'), 'guid'),
        description_content=[Cast('project__name', output_field=CharField())],
        project_field='project')


def _get_matching_individuals(query, project_guids):
    return _get_matching_objects(
        query, project_guids, Individual,
        core_fields=['display_name', 'individual_id'],
        href_expression=Concat(Value('/project/'), 'family__project__guid', Value('/family_page/'), 'family__guid'),
        description_content=[
            Cast('family__project__name', output_field=CharField()),
            Value(': family '),
            Coalesce(NullIf('family__display_name', Value('')), NullIf('family__family_id', Value(''))),
        ],
        project_field='family__project')


def _get_matching_project_groups(query, project_guids):
    return _get_matching_objects(
        query, project_guids, ProjectCategory,
        core_fields=['name'],
        href_expression=F('guid'),
        project_field='projects',
        select_related_project=False,
        exclude_criteria={'name': ANALYST_PROJECT_CATEGORY}
    )


def _get_matching_genes(query, *args):
    """Returns genes that match the given query string, and that the user can view.

    Args:
       user: Django user
       query: String typed into the awesomebar
    Returns:
       Sorted list of matches where each match is a dictionary of strings
    """
    result = []
    for g in get_queried_genes(query, MAX_RESULTS_PER_CATEGORY):
        if query.lower() in g['gene_id'].lower():
            title = g['gene_id']
            description = g['gene_symbol']
        else:
            title = g['gene_symbol']
            description = g['gene_id']

        result.append({
            'key': g['gene_id'],
            'title': title,
            'description': '('+description+')' if description else '',
            'href': '/summary_data/gene_info/'+g['gene_id'],
        })

    return result


def _get_matching_omim(query, *args):
    """Returns OMIM records that match the given query string"""
    records = Omim.objects.filter(
        Q(phenotype_mim_number__icontains=query) | Q(phenotype_description__icontains=query)
    ).filter(phenotype_mim_number__isnull=False).annotate(
        description_start=ExpressionWrapper(Q(phenotype_description__istartswith=query), output_field=BooleanField()),
        mim_number_start=ExpressionWrapper(Q(phenotype_mim_number__istartswith=query), output_field=BooleanField()),
    ).only('phenotype_mim_number', 'phenotype_description').order_by(
        '-description_start', '-mim_number_start', 'phenotype_description').distinct()[:MAX_RESULTS_PER_CATEGORY]
    result = []
    for record in records:
        result.append({
            'key': record.phenotype_mim_number,
            'title': record.phenotype_description,
            'description': '({})'.format(record.phenotype_mim_number) if record.phenotype_mim_number else None,
        })

    return result


def _get_matching_hpo_terms(query, *args):
    """Returns OMIM records that match the given query string"""
    records = HumanPhenotypeOntology.objects.filter(
        Q(hpo_id__icontains=query) | Q(name__icontains=query)
    ).annotate(
        name_start=ExpressionWrapper(Q(name__istartswith=query), output_field=BooleanField()),
        hpo_id_start=ExpressionWrapper(Q(hpo_id__istartswith=query), output_field=BooleanField()),
    ).only('hpo_id', 'name', 'category_id').order_by(
        '-name_start', '-hpo_id_start', 'name').distinct()[:MAX_RESULTS_PER_CATEGORY]
    result = []
    for record in records:
        result.append({
            'key': record.hpo_id,
            'title': record.name,
            'description': '({})'.format(record.hpo_id),
            'category': record.category_id,
        })

    return result


CATEGORY_MAP = {
    'genes': _get_matching_genes,
    'omim': _get_matching_omim,
    'hpo_terms': _get_matching_hpo_terms,
}
PROJECT_SPECIFIC_CATEGORY_MAP = {
    'projects': _get_matching_projects,
    'families': _get_matching_families,
    'analysis_groups': _get_matching_analysis_groups,
    'individuals': _get_matching_individuals,
    'project_groups': _get_matching_project_groups,
}
CATEGORY_MAP.update(PROJECT_SPECIFIC_CATEGORY_MAP)
DEFAULT_CATEGORIES = ['projects', 'families', 'analysis_groups', 'individuals', 'genes']


@login_and_policies_required
@require_GET
def awesomebar_autocomplete_handler(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q').strip()
    if not query:
        return create_json_response({'matches': {}})

    categories = request.GET.get('categories').split(',') if request.GET.get('categories') else DEFAULT_CATEGORIES

    project_guids = get_project_guids_user_can_view(request.user, limit_data_manager=False) if any(
        category for category in categories if category in PROJECT_SPECIFIC_CATEGORY_MAP) else None

    results = {
        category: {'name': _to_title_case(category), 'results': CATEGORY_MAP[category](query, project_guids)}
        for category in categories
    }

    return create_json_response({'matches': {k: v for k, v in results.items() if v['results']}})
