from pprint import pprint

def get_mpc_vds(hail_context, genome_version):
    if genome_version == "37":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh37/MPC/fordist_constraint_official_mpc_values.vds'
    elif genome_version == "38":
        mpc_vds_path = 'gs://seqr-reference-data/GRCh38/MPC/fordist_constraint_official_mpc_values.liftover.GRCh38.vds'
    else:
        raise ValueError("Invalid genome_version: " + str(genome_version))

    mpc_vds = (
        hail_context
            .read(mpc_vds_path)
            .annotate_variants_expr("""
                va.for_seqr.MPC = va.info.MPC,
                va.for_seqr.fitted_score = va.info.fitted_score,
                va.for_seqr.mis_badness = va.info.mis_badness,
                va.for_seqr.obs_exp = va.info.obs_exp
                """)
            .annotate_variants_expr("va = select(va, for_seqr)")
    )

    #pprint(mpc_vds.variant_schema)

    return mpc_vds