from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr

MPC_INFO_FIELDS = """
    MPC: Double,
    fitted_score: Double,
    mis_badness: Double,
    obs_exp: Double,
"""


def add_mpc_from_vds(hail_context, vds, genome_version, root="va.mpc", info_fields=MPC_INFO_FIELDS, verbose=True):
    """Add MPC annotations [Samocha 2017] to the vds"""

    if genome_version == "37":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh37/MPC/fordist_constraint_official_mpc_values.vds'
    elif genome_version == "38":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh38/MPC/fordist_constraint_official_mpc_values.liftover.GRCh38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    mpc_vds = hail_context.read(mpc_vds_path).split_multi()

    expr = convert_vds_schema_string_to_annotate_variants_expr(
        root=root,
        other_source_fields=info_fields,
        other_source_root="vds.info",
    )

    if verbose:
        print(expr)
        #print("\n==> mpc summary: ")
        #print(mpc_vds.summarize())

    return vds.annotate_variants_vds(mpc_vds, expr=expr)
