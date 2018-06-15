"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.model_utils import update_seqr_model
from seqr.models import Project, Family, Individual, Sample, Dataset, _slugify, CAN_EDIT, IS_OWNER
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.phenotips_api import create_phenotips_user, _get_phenotips_uname_and_pwd_for_project
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_project
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual, \
    ReferencePopulation, ProjectTag


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_project_handler(request):
    """Create a new project.

    HTTP POST
        Request body - should contain json params:
            name: Project name
            description: Project description

        Response body - will be json with the following structure, representing the ,created project:
            {
                'projectsByGuid':  { <projectGuid1> : { ... <project key-value pairs> ... } }
            }

    """
    request_json = json.loads(request.body)

    name = request_json.get('name')
    if not name:
        return create_json_response({}, status=400, reason="'Name' cannot be blank")

    description = request_json.get('description', '')

    #if not created:
    #    return create_json_response({}, status=400, reason="A project named '%(name)s' already exists" % locals())

    project = create_project(name, description=description, user=request.user)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_handler(request, project_guid):
    """Update project metadata - including one or more of these fields: name, description

    Args:
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'form' : {
                'name':  <project name>,
                'description': <project description>,
            }
        }

        Response body - will contain the following structure, representing the updated project:
            {
                'projectsByGuid':  {
                    <projectGuid1> : { ... <project key-value pairs> ... }
                }
            }

    """

    project = Project.objects.get(guid=project_guid)

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    if 'name' in request_json:
        update_seqr_model(project, name=request_json.get('name'))

    if 'description' in request_json:
        update_seqr_model(project, description=request_json.get('description'))

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_handler(request, project_guid):
    """Delete project - request handler.

    Args:
        project_guid (string): GUID of the project to delete
    """

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=IS_OWNER)

    delete_project(project)

    return create_json_response({
        'projectsByGuid': {
            project.guid: None
        },
    })


def create_project(name, description=None, user=None):
    """Creates a new project.

    Args:
        name (string): Project name
        description (string): optional description
        user (object): Django user that is creating this project
    """
    if not name:
        raise ValueError("Name not specified: %s" % (name,))

    project, created = Project.objects.get_or_create(
        created_by=user,
        name=name,
        description=description,
    )

    if created:
        base_project = _deprecated_create_original_project(project)

        project.deprecated_project_id = base_project.project_id
        project.save()

        _enable_phenotips_for_project(project)

    _deprecated_add_default_tags_to_original_project(project)

    # TODO: add custom populations

    return project


def delete_project(project):
    """Delete project.

    Args:
        project (object): Django ORM model for the project to delete
    """

    _deprecated_delete_original_project(project)

    Dataset.objects.filter(project=project).delete()
    Sample.objects.filter(individual__family__project=project).delete()
    Individual.objects.filter(family__project=project).delete()
    Family.objects.filter(project=project).delete()
    project.delete()

    # TODO delete PhenoTips, etc. and other objects under this project


def _enable_phenotips_for_project(project):
    """Creates 2 users in PhenoTips for this project (one that will be view-only and one that'll
    have edit permissions for patients in the project).
    """
    project.is_phenotips_enabled = True
    project.phenotips_user_id = _slugify(project.name)

    # view-only user
    username, password = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    create_phenotips_user(username, password)

    # user with edit permissions
    username, password = _get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    create_phenotips_user(username, password)
    project.save()


def _deprecated_create_original_project(project):
    """DEPRECATED - create project in original xbrowse schema to keep things in sync.

    Args:
        project (object): new-style seqr project model
    """

    # keep new seqr.Project model in sync with existing xbrowse_server.base.models
    base_project, created = BaseProject.objects.get_or_create(
        project_id=_slugify(project.name)
    )

    if created:
        logger.info("Created base project %s" % base_project)

    base_project.project_name = project.name
    base_project.description = project.description
    base_project.seqr_project = project
    base_project.save()

    for reference_population_id in ["gnomad-genomes2", "gnomad-exomes2", "topmed"]:
        try:
            population = ReferencePopulation.objects.get(slug=reference_population_id)
            logger.info("Adding population " + reference_population_id + " to project " + str(project))
            base_project.private_reference_populations.add(population)
        except Exception as e:
            logger.error("Unable to add reference population %s: %s" % (reference_population_id, e))
            
    return base_project


def _deprecated_delete_original_project(project):
    """DEPRECATED - delete project in original xbrowse schema to keep things in sync.
    Args:
        project (object): new-style seqr project model
    """

    for base_project in BaseProject.objects.filter(project_id=project.deprecated_project_id):
        BaseIndividual.objects.filter(family__project=base_project).delete()
        BaseFamily.objects.filter(project=base_project).delete()
        base_project.delete()


def _deprecated_add_default_tags_to_original_project(project):
    DEFAULT_VARIANT_TAGS = [
        {
            "order": 1,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Novel gene and phenotype",
            "color": "#03441E",
            "description": "Gene not previously associated with a Mendelian condition",
        },
        {
            "order": 2,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Novel gene for known phenotype",
            "color": "#096C2F",
            "description": "Phenotype known but no causal gene known (includes adding to locus heterogeneity)",
        },
        {
            "order": 3,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Phenotype expansion",
            "color": "#298A49",
            "description": "Phenotype studies have different clinical characteristics and/or natural history"
        },
        {
            "order": 4,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Phenotype not delineated",
            "color": "#44AA60",
            "description": "Phenotype not previously delineated (i.e. no MIM #)"
        },
        {
            "order": 5,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Novel mode of inheritance",
            "color": "#75C475",
            "description": "Gene previously associated with a Mendelian condition but mode of inheritance is different",
        },
        {
            "order": 6,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 2 - Novel gene and phenotype",
            "color": "#0B437D",
            "description": "Gene not previously associated with a Mendelian condition"
        },
        {
            "order": 7,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 2 - Novel gene for known phenotype",
            "color": "#1469B0",
            "description": "Phenotype known but no causal gene known (includes adding to locus heterogeneity)",
        },
        {
            "order": 7.5,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 2 - Phenotype expansion",
            "description": "Phenotype studies have different clinical characteristics and/or natural history",
            "color": "#318CC2"
        },
        {
            "order": 8, "category":
            "CMG Discovery Tags",
            "tag_name": "Tier 2 - Phenotype not delineated",
            "color": "#318CC2",
            "description": "Phenotype not previously delineated (i.e. no OMIM #)",
        },
        {
            "order": 9,
            "category": "CMG Discovery Tags",
            "tag_name": "Known gene for phenotype",
            "color": "#030A75",
            "description": "The gene overlapping the variant has been previously associated with the same phenotype presented by the patient",
        },
        {
            "order": 10,
            "category": "Collaboration",
            "tag_name": "Review",
            "description": "Variant and/or gene of interest for further review",
            "color": "#668FE3"
        },
        {
            "order": 10.3,
            "category": "Collaboration",
            "tag_name": "Send for Sanger validation",
            "description": "Send for Sanger validation",
            "color": "#f1af5f"
        },
        {
            "order": 10.31,
            "category": "Collaboration",
            "tag_name": "Sanger validated",
            "description": "Confirmed by Sanger sequencing",
            "color": "#b2df8a",
        },
        {
            "order": 10.32,
            "category": "Collaboration",
            "tag_name": "Sanger did not validate",
            "description": "Sanger did not validate",
            "color": "#823a3a",
        },
        {
            "order": 10.5,
            "category": "Collaboration",
            "tag_name": "Excluded",
            "description": "Variant and/or gene you previously reviewed but do not think it contributing to the phenotype in this case. To help other members of your team (and yourself), please consider also adding a note with details of why you reprioritized this variant.",
            "color": "#555555"
        },
        {
            "order": 11,
            "category": "ACMG Variant Classification",
            "tag_name": "Pathogenic",
            "description": "",
            "color": "#B92732"
        },
        {
            "order": 12,
            "category": "ACMG Variant Classification",
            "tag_name": "Likely Pathogenic",
            "description": "",
            "color": "#E48065"
        },
        {
            "order": 13,
            "category": "ACMG Variant Classification",
            "tag_name": "VUS",
            "description": "Variant of uncertain significance",
            "color": "#FACCB4"
        },
        {
            "order": 14,
            "category": "ACMG Variant Classification",
            "tag_name": "Likely Benign",
            "description": "",
            "color": "#6BACD0"
        },
        {
            "order": 15,
            "category": "ACMG Variant Classification",
            "tag_name": "Benign",
            "description": "",
            "color": "#2971B1"
        },
        {
            "order": 16,
            "category": "ACMG Variant Classification",
            "tag_name": "Secondary finding",
            "color": "#FED82F",
            "description": "The variant was found during the course of searching for candidate disease genes and can be described as pathogenic or likely pathogenic according to ACMG criteria and overlaps a gene known to cause a disease that differs from the patient's primary indication for sequencing."
        },
        {
            "order": 17,
            "category": "Data Sharing",
            "tag_name": "MatchBox (MME)",
            "description": "Gene, variant, and phenotype to be submitted to Matchmaker Exchange",
            "color": "#531B86"
        },
        {
            "order": 18,
            "category": "Data Sharing",
            "tag_name": "Submit to Clinvar",
            "description": "By selecting this tag, you are notifying CMG staff that this variant should be submitted to ClinVar. Generally, this is for pathogenic or likely pathogenic variants in known disease genes or for any benign or likely benign variants that are incorrectly annotated in ClinVar. Please also add a note that describes supporting evidence for how you interpreted this variant.",
            "color": "#8A62AE"
        },
        {
            "order": 19,
            "category": "Data Sharing",
            "tag_name": "Share with KOMP",
            "description": "To mark a variant/gene that you would like us to share with the Mouse Knockout Project for their knockout and phenotyping pipeline. Add additional notes to comments as needed.",
            "color": "#ad627a"
        },
    ]

    base_project = BaseProject.objects.get(project_id=project.deprecated_project_id)
    for r in DEFAULT_VARIANT_TAGS:
        t, _ = ProjectTag.objects.get_or_create(project=base_project, tag=r['tag_name'])
        t.order = r['order']
        t.category = r['category']
        t.title = r['description']
        t.color = r['color']
        t.save()




