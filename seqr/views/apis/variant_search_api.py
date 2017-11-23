import json
import requests

from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, CAN_VIEW, Sample, Dataset
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants_handler(request, project_guid):
    """Search variants.

    Args:
        project_guid (string): GUID of the project to query


    HTTP POST
        Reqeust body:
            {
                filters:
                {
                    project_guids:
                    {
                        project_guid1
                        {
                            family_guids: {
                                family_guid1
                                family_guid2
                                {

                                },
                            },

                            dataset_guids:
                            {
                                WES, WGS, CNV, RNA_splice datasets
                            },
                        },

                        project_guid2
                        {
                            # empty means query all families in project
                            # empty dataset means query all datasets
                        },
                    },
                }

                projection: "by_family" | "by_variant" | "by_gene"  (1 row per..)




            }
        Response body: will be json with the delete projectGuid mapped to the special 'DELETE' keyword:
            {
                'projectsByGuid':  { <projectGuid1> : ... }
            }

    """

    # if project not specified, search all projects the user has access to
    project = Project.objects.get(guid=project_guid)

    # Query Params:
    #    list of individuals and how to filter on their genotype, allele balance, etc.
    #    list of datasets
    #    intervals
    #

    # query1: are there any family ids that are invalid, or that the user doesn't have permissions to access?

    # query2: are there families that dont' have data?

    # get all elasticsearch datasets being queried (or include them in the query


    # for each family being queried, get affected status of individuals
    #


    # check permissions
    if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
        raise PermissionDenied


    # for the families being searched, look up available samples and datasets to query

    # create elasticsearch filters


    request_json = json.loads(request.body)


    #if 'form' not in request_json:
    #    return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")


    results = requests.post('http://localhost:6060/', json={
        "page": 1,
        "limit": 100,
        "genotype_filters": {
            "1877nih": {"num_alt": 1},
            "22067nih": {"num_alt": 2},
        }
    })


    print(results.status_code)

    results = json.loads(results.text)

    # TODO delete Family, Individual, and other objects under this project
    return create_json_response({
        'variants': results,
    })



_SAMPLE_TYPES = set([sample_type[0] for sample_type in Sample.SAMPLE_TYPE_CHOICES])
_ANALYSIS_TYPES = set([analysis_type[0] for analysis_type in Dataset.ANALYSIS_TYPE_CHOICES])

def _retrieve_datasets(
        cursor,
        project_guids,
        family_guids=None,
        individual_guids=None,
        sample_types=None,
        analysis_types=None,
        only_loaded_datasets=True
):
    """Retrieves information on datasets that match all of the given critera.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        project_guids (list): List of projects
        family_guids (list): (optional) only consider datasets that have samples for individuals in these families.
        individual_guids (list): (optional) only consider datasets that have samples for these individuals
        sample_types (list): (optional) only consider datasets that have samples of these types (eg. "WES", "WGS", "RNA", etc.)
            See models.Sample.SAMPLE_TYPE_CHOICES for the full list of possible values.
        analysis_types (list): (optional) only consider datasets with this analysis type (eg. "SV", "VARIANT_CALLS", etc.)
            See models.Dataset.ANALYSIS_TYPE_CHOICES for the full list of possible values.
        only_loaded_datasets (bool): only return loaded datasets
    Returns:
        2-tuple with dictionaries: (families_by_guid, individuals_by_guid)
    """

    # make sure the user has permissions to access these projects
    # SQL injection

    WHERE_clause = "p.guid IN (" + ", ".join("%s"*len(project_guids)) + ")"
    WHERE_clause_args = list(project_guids)

    if family_guids is not None:
        WHERE_clause += " AND "
        WHERE_clause += "f.guid IN (" + ", ".join("%s"*len(family_guids)) + ")"
        WHERE_clause_args = list(family_guids)

    if individual_guids is not None:
        WHERE_clause += " AND "
        WHERE_clause += "i.guid IN (" + ", ".join("%s"*len(individual_guids)) + ")"
        WHERE_clause_args = list(individual_guids)

    if sample_types is not None:
        unexpected_sample_types = set(sample_types) - set(_SAMPLE_TYPES)
        if len(unexpected_sample_types) > 0:
            raise ValueError("Invalid sample_type(s): %s" % (unexpected_sample_types,))
        WHERE_clause += " AND "
        WHERE_clause += "s.sample_type IN (" + ", ".join("%s"*len(sample_types)) + ")"
        WHERE_clause_args = list(sample_types)

    if analysis_types is not None:
        unexpected_analysis_types = set(analysis_types) - set(_ANALYSIS_TYPES)
        if len(unexpected_analysis_types) > 0:
            raise ValueError("Invalid analysis_type(s): %s" % (unexpected_analysis_types,))
        WHERE_clause += " AND "
        WHERE_clause += "d.analysis_type IN (" + ", ".join("%s"*len(analysis_types)) + ")"
        WHERE_clause_args = list(analysis_types)

    if only_loaded_datasets:
        WHERE_clause += " AND d.is_loaded=TRUE "

    datasets_query = """
        SELECT DISTINCT
          p.guid AS project_guid,
          p.name AS project_name,
          f.guid AS family_guid,
          f.family_id AS family_id,
          i.guid AS individual_guid,
          i.individual_id AS individual_id,
          i.display_name AS individual_display_name,
          s.sample_type AS sample_type,
          s.sample_id AS sample_id,
          d.dataset_id AS dataset_id,
          d.dataset_location AS dataset_location,
          d.analysis_type AS dataset_analysis_type,
          d.is_loaded AS dataset_is_loaded,
          d.loaded_date AS dataset_loaded_date
        FROM seqr_project AS p
          JOIN seqr_family AS f ON f.project_id=p.id
          JOIN seqr_individual AS i ON i.family_id=f.id
          JOIN seqr_sample AS s ON s.individual_id=i.id
          JOIN seqr_dataset_samples AS ds ON ds.sample_id=s.id
          JOIN seqr_dataset AS d ON d.id=ds.dataset_id
        WHERE %s
    """.strip() % WHERE_clause

    cursor.execute(datasets_query, WHERE_clause_args)

    columns = [col[0] for col in cursor.description]

    families_by_guid = {}
    individuals_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        family_guid = record['family_guid']
        if family_guid not in families_by_guid:
            families_by_guid[family_guid] = _get_json_for_family_fields(record)
            families_by_guid[family_guid]['individualGuids'] = set()

        individual_guid = record['individual_guid']
        if individual_guid not in individuals_by_guid:
            individuals_by_guid[individual_guid] = _get_json_for_individual_fields(record)
            phenotips_data = individuals_by_guid[individual_guid]['phenotipsData']
            if phenotips_data:
                try:
                    individuals_by_guid[individual_guid]['phenotipsData'] = json.loads(phenotips_data)
                except Exception as e:
                    logger.error("Couldn't parse phenotips: %s", e)
            individuals_by_guid[individual_guid]['sampleGuids'] = set()

            families_by_guid[family_guid]['individualGuids'].add(individual_guid)

    return families_by_guid, individuals_by_guid


def _add_variant_filters(es):
    """
           self.variant_types = kwargs.get('variant_types')
        self.so_annotations = kwargs.get('so_annotations')  # todo: rename (and refactor)
        self.annotations = kwargs.get('annotations', {})
        self.ref_freqs = kwargs.get('ref_freqs')
        self.locations = kwargs.get('locations')
        self.genes = kwargs.get('genes')
        self.exclude_genes = kwargs.get('exclude_genes')
    :param es:
    :return:
    """

def _add_genotype_filters(es):
    pass


"""
Current search API:
    project_id:rare_genomes_project
    family_id:RGP_23
    search_mode:custom_inheritance
    variant_filter:{
        "so_annotations":["stop_gained","splice_donor_variant","splice_acceptor_variant","stop_lost","initiator_codon_variant","start_lost","missense_variant","protein_altering_variant","frameshift_variant","inframe_insertion","inframe_deletion"],
        "ref_freqs":[["1kg_wgs_phase3",0.0005],["1kg_wgs_phase3_popmax",0.001],["exac_v3",0.001],["exac_v3_popmax",0.0005],["gnomad_exomes",0.0005],["gnomad_exomes_popmax",0.0005],["gnomad_genomes",0.001],["gnomad_genomes_popmax",0.0005],["topmed",0.01]],
        "annotations":{},
    },
    quality_filter:{"min_gq":0,"min_ab":0},
    genotype_filter:{"RGP_23_1":"ref_alt","RGP_23_2":"alt_alt","RGP_23_3":"has_alt"},


"""

"""
individuals:
    - projects, projectGroups
    - families, familyGroups

datasets:
    - WES_variants, WGS_variants, WES_CNVs, WGS_CNVs

loci:
    - genes, transcripts, ranges, geneLists

allele info:
    - VEP annotation, consequence, clinvar

genotypes:
    - inheritance mode =>
    - allele balance, GQ, DP
"""