import json
import requests

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, CAN_VIEW
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

    # get all elasticsearch datasets being queried



    # check permissions
    if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
        raise PermissionDenied


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