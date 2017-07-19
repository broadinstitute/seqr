from pprint import pprint

from utils.vds_schema_string_utils import convert_vds_schema_string_to_annotate_variants_expr

def add_mpc_data_struct(hail_context, vds, genome_version, root="va.mpc"):
    """Add MPC annotations [Samocha 2017] to the vds"""

    if genome_version == "37":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh37/MPC/fordist_constraint_official_mpc_values.vds'
    elif genome_version == "38":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh38/MPC/fordist_constraint_official_mpc_values.liftover.GRCh38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    mpc_vds = hail_context.read(mpc_vds_path)

    return vds.annotate_variants_vds(mpc_vds, expr="""
        %(root)s.MPC = vds.info.MPC,
        %(root)s.fitted_score = vds.info.fitted_score,
        %(root)s.mis_badness = vds.info.mis_badness,
        %(root)s.obs_exp = vds.info.obs_exp
        """ % locals())
