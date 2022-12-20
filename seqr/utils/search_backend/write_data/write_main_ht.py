import argparse
import hail as hl

VARIANT_TYPE = 'VARIANTS'

CLINVAR_SIGNIFICANCES = {sig: i for i, sig in enumerate([
    'Pathogenic', 'Pathogenic,_risk_factor', 'Pathogenic,_Affects', 'Pathogenic,_drug_response',
    'Pathogenic,_drug_response,_protective,_risk_factor', 'Pathogenic,_association', 'Pathogenic,_other',
    'Pathogenic,_association,_protective', 'Pathogenic,_protective', 'Pathogenic/Likely_pathogenic',
    'Pathogenic/Likely_pathogenic,_risk_factor', 'Pathogenic/Likely_pathogenic,_drug_response',
    'Pathogenic/Likely_pathogenic,_other', 'Likely_pathogenic,_risk_factor', 'Likely_pathogenic',
    'Conflicting_interpretations_of_pathogenicity', 'Conflicting_interpretations_of_pathogenicity,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_Affects',
    'Conflicting_interpretations_of_pathogenicity,_association,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_other,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_association',
    'Conflicting_interpretations_of_pathogenicity,_drug_response',
    'Conflicting_interpretations_of_pathogenicity,_drug_response,_other',
    'Conflicting_interpretations_of_pathogenicity,_other', 'Uncertain_significance',
    'Uncertain_significance,_risk_factor', 'Uncertain_significance,_Affects', 'Uncertain_significance,_association',
    'Uncertain_significance,_other', 'Affects', 'Affects,_risk_factor', 'Affects,_association', 'other', 'NA',
    'risk_factor', 'drug_response,_risk_factor', 'association', 'confers_sensitivity', 'drug_response', 'not_provided',
    'Likely_benign,_drug_response,_other', 'Likely_benign,_other', 'Likely_benign', 'Benign/Likely_benign,_risk_factor',
    'Benign/Likely_benign,_drug_response', 'Benign/Likely_benign,_other', 'Benign/Likely_benign', 'Benign,_risk_factor',
    'Benign,_confers_sensitivity', 'Benign,_association,_confers_sensitivity', 'Benign,_drug_response', 'Benign,_other',
    'Benign,_protective', 'Benign', 'protective,_risk_factor', 'protective',
])}
HGMD_SIGNIFICANCES = {sig: i for i, sig in enumerate([
    'DM', 'DM?', 'DP', 'DFP', 'FP', 'FTV', 'R',
])}

CONSEQUENCE_RANKS = {c: i for i, c in enumerate([
    "transcript_ablation",
    "splice_acceptor_variant",
    "splice_donor_variant",
    "stop_gained",
    "frameshift_variant",
    "stop_lost",
    "start_lost",  # new in v81
    "initiator_codon_variant",  # deprecated
    "transcript_amplification",
    "inframe_insertion",
    "inframe_deletion",
    "missense_variant",
    "protein_altering_variant",  # new in v79
    "splice_region_variant",
    "incomplete_terminal_codon_variant",
    "start_retained_variant",
    "stop_retained_variant",
    "synonymous_variant",
    "coding_sequence_variant",
    "mature_miRNA_variant",
    "5_prime_UTR_variant",
    "3_prime_UTR_variant",
    "non_coding_transcript_exon_variant",
    "non_coding_exon_variant",  # deprecated
    "intron_variant",
    "NMD_transcript_variant",
    "non_coding_transcript_variant",
    "nc_transcript_variant",  # deprecated
    "upstream_gene_variant",
    "downstream_gene_variant",
    "TFBS_ablation",
    "TFBS_amplification",
    "TF_binding_site_variant",
    "regulatory_region_ablation",
    "regulatory_region_amplification",
    "feature_elongation",
    "regulatory_region_variant",
    "feature_truncation",
    "intergenic_variant",
])}

SIFT_FATHMM_MAP = {val: i for i, val in enumerate(['D', 'T'])}
POLYPHEN_MAP = {val: i for i, val in enumerate(['D', 'P', 'B'])}
MUT_TASTER_MAP = {val: i for i, val in enumerate(['D', 'A', 'N', 'P'])}


def predictor_expr(field, map):
    return hl.bind(
        lambda pred_key: hl.or_missing(hl.is_defined(pred_key), hl.dict(map)[pred_key]),
        field.split(';').find(lambda p: p != '.'),
    )


ANNOTATIONS = {
    VARIANT_TYPE: {
        'callset': lambda ht: hl.struct(
            AF=ht.AF,
            AC=ht.AC,
            AN=ht.AN,
        ),
        'clinvar': lambda ht: hl.or_missing(hl.is_defined(ht.clinvar.clinical_significance), hl.struct(
            clinical_significance_id=hl.dict(CLINVAR_SIGNIFICANCES)[ht.clinvar.clinical_significance],
            alleleId=ht.clinvar.allele_id,
            goldStars=ht.clinvar.gold_stars,
        )),
        'dbnsfp': lambda ht: hl.struct(
            SIFT_pred_id=predictor_expr(ht.dbnsfp.SIFT_pred, SIFT_FATHMM_MAP),
            Polyphen2_HVAR_pred_id=predictor_expr(ht.dbnsfp.Polyphen2_HVAR_pred, POLYPHEN_MAP),
            MutationTaster_pred_id=predictor_expr(ht.dbnsfp.MutationTaster_pred, MUT_TASTER_MAP),
            FATHMM_pred_id=predictor_expr(ht.dbnsfp.FATHMM_pred, SIFT_FATHMM_MAP),
            REVEL_score=hl.parse_float(ht.dbnsfp.REVEL_score),
        ),
        'hgmd': lambda ht: hl.or_missing(hl.is_defined(ht.hgmd['class']), hl.struct(
            class_id=hl.dict(HGMD_SIGNIFICANCES)[ht.hgmd['class']],
            accession=ht.hgmd.accession,
        )),
        'mpc': lambda ht: hl.struct(MPC=hl.parse_float(ht.mpc.MPC)),
        'sortedTranscriptConsequences': lambda ht: ht.sortedTranscriptConsequences.map(
            lambda t: t.select(
                'amino_acids', 'biotype', 'canonical', 'codons', 'gene_id', 'hgvsc', 'hgvsp', 'lof', 'lof_filter',
                'lof_flags', 'lof_info', 'transcript_id', 'transcript_rank',
                sorted_consequence_ids=hl.sorted(t.consequence_terms.map(lambda c: hl.dict(CONSEQUENCE_RANKS)[c])),
            )
        ),
        # TODO map screen -> region_type
    },
}

SELECT_FIELDS = {
    VARIANT_TYPE: [
        'cadd', 'eigen', 'exac', 'filters', 'gnomad_exomes', 'gnomad_genomes', 'gnomad_non_coding_constraint',
        'originalAltAlleles', 'primate_ai', 'rg37_locus', 'rsid', 'screen', 'splice_ai', 'topmed', 'variantId', 'xpos',
    ],
}


def _get_file_path(file):
    return f'gs://hail-backend-datasets/{file}.mt'


def _get_interval_file_path(file):
    return f'gs://hail-backend-datasets/{file}.interval_annotations.ht'


def add_interval_ref_data(file):
    # TODO on new datasets this will already be annotated in the pipeline
    hl._set_flags(use_new_shuffle='1')
    ht = hl.read_matrix_table(_get_file_path(file)).rows()
    interval_ref_data = hl.read_table('gs://hail-backend-datasets/combined_interval_reference_data.ht').index(
        ht.locus, all_matches=True
    )
    ht = ht.annotate(
        gnomad_non_coding_constraint=hl.struct(
            z_score=interval_ref_data.filter(
                lambda x: hl.is_defined(x.gnomad_non_coding_constraint["z_score"])
            ).gnomad_non_coding_constraint.z_score.first()
        ),
        screen=hl.struct(region_type=interval_ref_data.flatmap(lambda x: x.screen["region_type"])),
    )
    ht.write(_get_interval_file_path(file))


def write_main_ht(file, data_type):
    ht = hl.read_table(_get_interval_file_path(file)) if data_type == VARIANT_TYPE else \
        hl.read_matrix_table(_get_file_path(file)).rows()

    ht = ht.select_globals()
    ht = ht.select(*SELECT_FIELDS[data_type], **{k: v(ht) for k, v in ANNOTATIONS[data_type].items()})
    ht.write(f'gs://hail-backend-datasets/{file}.ht')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('data_type', choices=ANNOTATIONS.keys())
    p.add_argument('--add-interval-ref', action='store_true')
    args = p.parse_args()

    if args.add_interval_ref:
        add_interval_ref_data(args.file)
    else:
        write_main_ht(args.file, args.data_type)