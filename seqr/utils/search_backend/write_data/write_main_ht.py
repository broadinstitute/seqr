import argparse
import hail as hl

VARIANT_TYPE = 'VARIANTS'
SV_TYPE = 'SV'
GCNV_TYPE = 'gCNV'
MITO_TYPE = 'MITO'

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
SCREEN_MAP = {c: i for i, c in enumerate(['CTCF-bound', 'CTCF-only', 'DNase-H3K4me3', 'PLS', 'dELS', 'pELS'])}

SV_CONSEQUENCE_RANKS = {c: i for i, c in enumerate([
    'COPY_GAIN', 'LOF', 'DUP_LOF', 'DUP_PARTIAL', 'INTRONIC', 'INV_SPAN', 'NEAREST_TSS', 'PROMOTER', 'UTR',
])}
SV_TYPE_MAP = {c: i for i, c in enumerate([
    'gCNV_DEL', 'gCNV_DUP', 'BND', 'CPX', 'CTX', 'DEL', 'DUP', 'INS', 'INV',
])}
SV_TYPE_DETAIL_MAP = {c: i for i, c in enumerate([
    'INS_iDEL', 'INVdel', 'INVdup', 'ME', 'ME:ALU', 'ME:LINE1', 'ME:SVA', 'dDUP', 'dDUP_iDEL', 'delINV', 'delINVdel',
    'delINVdup', 'dupINV', 'dupINVdel', 'dupINVdup',
])}

CHROMOSOMES = [
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21',
    '22', 'X', 'Y', 'M',
]
CHROM_NUMBER_TO_CHROM = hl.literal({i: chrom for i, chrom in enumerate(CHROMOSOMES)})

SIFT_FATHMM_MAP = {val: i for i, val in enumerate(['D', 'T'])}
POLYPHEN_MAP = {val: i for i, val in enumerate(['D', 'P', 'B'])}
MUT_TASTER_MAP = {val: i for i, val in enumerate(['D', 'A', 'N', 'P'])}

MITOTIP_MAP = {val: i for i, val in enumerate([
    'likely_pathogenic',  'possibly_pathogenic', 'possibly_benign', 'likely_benign',
])}


def predictor_expr(field, map):
    return hl.bind(
        lambda pred_key: hl.or_missing(hl.is_defined(pred_key), hl.dict(map)[pred_key]),
        field.split(';').find(lambda p: p != '.'),
    )


VARIANT_ANNOTATIONS = {
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
    'sortedTranscriptConsequences': lambda ht: ht.sortedTranscriptConsequences.map(
        lambda t: t.select(
            'amino_acids', 'biotype', 'canonical', 'codons', 'gene_id', 'hgvsc', 'hgvsp', 'lof', 'lof_filter',
            'lof_flags', 'lof_info', 'transcript_id', 'transcript_rank',
            sorted_consequence_ids=hl.sorted(t.consequence_terms.map(lambda c: hl.dict(CONSEQUENCE_RANKS)[c])),
        )
    ),
}
ANNOTATIONS = {
    VARIANT_TYPE: {
        'hgmd': lambda ht: hl.or_missing(hl.is_defined(ht.hgmd['class']), hl.struct(
            class_id=hl.dict(HGMD_SIGNIFICANCES)[ht.hgmd['class']],
            accession=ht.hgmd.accession,
        )),
        'mpc': lambda ht: hl.struct(MPC=hl.parse_float(ht.mpc.MPC)),
        'screen': lambda ht: ht.screen.select(
            region_type_id=ht.screen.region_type.map(lambda r: hl.dict(SCREEN_MAP)[r]),
        ),
    },
    GCNV_TYPE: {
        'sv_callset': lambda ht: hl.struct(
            AF=ht.vaf,
            AC=ht.vac,
            AN=hl.int(ht.vac/ht.vaf),
            Hom=hl.missing(hl.dtype('int32')),
            Het=hl.missing(hl.dtype('int32')),
        ),
        'strvctvre': lambda ht: hl.struct(score=ht.strvctvre),
        'sortedTranscriptConsequences': lambda ht: hl.array(ht.geneIds.map(lambda gene: hl.Struct(
            gene_id=gene,
            major_consequence_id=hl.if_else(
                ht.cg_genes.contains(gene),
                SV_CONSEQUENCE_RANKS['COPY_GAIN'],
                hl.if_else(ht.lof_genes.contains(gene), SV_CONSEQUENCE_RANKS['LOF'],  hl.missing(hl.tint)),
            )
        ))),
        'svType_id': lambda ht: hl.dict(SV_TYPE_MAP)[ht.svType],
    },
    SV_TYPE: {
        'algorithms': lambda ht: hl.str(',').join(ht.algorithms),
        'bothsidesSupport': lambda ht: ht.bothsides_support,
        'cpxIntervals': lambda ht: ht.cpx_intervals,
        'filters': lambda ht: hl.set(ht.filters),
        'gnomad_svs': lambda ht: hl.or_missing(
            hl.is_defined(ht.gnomad_svs_AF), hl.struct(AF=ht.gnomad_svs_AF, ID=ht.gnomad_svs_ID)),
        'interval': lambda ht: hl.interval(
            hl.locus(hl.format('chr%s', ht.contig), ht.start, reference_genome='GRCh38'),
            hl.bind(
                lambda end_chrom, end_pos: hl.if_else(
                    ((ht.contig != end_chrom) | (ht.end != end_pos)) & (ht.svType != 'INS') & (
                        # This is to handle a bug in the SV pipeline, should not go to production
                        (ht.svType != 'CPX') | (hl.is_valid_locus(hl.format('chr%s', end_chrom), end_pos, 'GRCh38'))
                    ),
                    hl.locus(hl.format('chr%s', end_chrom), end_pos, reference_genome='GRCh38'),
                    hl.locus(hl.format('chr%s', ht.contig), ht.end, reference_genome='GRCh38')
                ),
                CHROM_NUMBER_TO_CHROM[hl.int(ht.xstop / 1e9) - 1],
                hl.int(ht.xstop % int(1e9)),
            ),
        ),
        'sortedTranscriptConsequences': lambda ht: ht.sortedTranscriptConsequences.map(
            lambda t: t.select('gene_id', major_consequence_id=hl.dict(SV_CONSEQUENCE_RANKS)[t.major_consequence])),
        'strvctvre': lambda ht: hl.struct(score=ht.StrVCTVRE_score),
        'sv_callset': lambda ht: hl.struct(
            AF=ht.sf,
            AC=ht.sc,
            AN=ht.sn,
            Hom=ht.sv_callset_Hom,
            Het=ht.sv_callset_Het,
        ),
        'svSourceDetail': lambda ht: hl.bind(
            lambda end_chrom, end_pos: hl.or_missing(
                ((ht.contig != end_chrom) | (ht.end != end_pos)) & (ht.svType == 'INS'),
                hl.struct(chrom=end_chrom),
            ),
            CHROM_NUMBER_TO_CHROM[hl.int(ht.xstop / 1e9) - 1],
            hl.int(ht.xstop % int(1e9)),
        ),
        'svType_id': lambda ht: hl.dict(SV_TYPE_MAP)[ht.svType],
        'svTypeDetail_id': lambda ht: hl.or_missing(
            hl.is_defined(ht.sv_type_detail), hl.dict(SV_TYPE_DETAIL_MAP)[ht.sv_type_detail]),
    },
    MITO_TYPE: {
        'callset_heteroplasmy': lambda ht: hl.struct(
            AF=ht.AF_het,
            AC=ht.AC_het,
            AN=ht.AN,
        ),
        'gnomad_mito': lambda ht: hl.struct(
            AF=ht.gnomad_mito.AF,
            AC=ht.gnomad_mito.AC,
            AN=ht.gnomad_mito.AN,
        ),
        'gnomad_mito_heteroplasmy': lambda ht: hl.struct(
            AF=ht.gnomad_mito.AF_het,
            AC=ht.gnomad_mito.AC_het,
            AN=ht.gnomad_mito.AN,
            max_hl=ht.gnomad_mito.max_hl,
        ),
        'helix': lambda ht: hl.struct(
            AF=ht.helix.AF,
            AC=ht.helix.AC,
            AN=ht.helix.AN,
        ),
        'helix_heteroplasmy': lambda ht: hl.struct(
            AF=ht.helix.AF_het,
            AC=ht.helix.AC_het,
            AN=ht.helix.AN,
            max_hl=ht.helix.max_hl,
        ),
        'mitimpact': lambda ht: hl.struct(score=ht.mitimpact_apogee),
        'hmtvar': lambda ht: hl.struct(score=ht.hmtvar_hmtVar),
        'mitotip': lambda ht: hl.struct(trna_prediction_id=predictor_expr(ht.mitotip_mitoTIP, MITOTIP_MAP)),
        'haplogroup': lambda ht: hl.struct(
            is_defining=hl.if_else(ht.hap_defining_variant, 0, hl.missing(hl.tint)),
        ),
    },
}
ANNOTATIONS[VARIANT_TYPE].update(VARIANT_ANNOTATIONS)
ANNOTATIONS[MITO_TYPE].update(VARIANT_ANNOTATIONS)

VARIANT_SELECT_FIELDS = ['filters', 'rg37_locus', 'rsid', 'variantId', 'xpos']
SELECT_FIELDS = {
    VARIANT_TYPE: VARIANT_SELECT_FIELDS + [
        'cadd', 'eigen', 'exac', 'gnomad_exomes', 'gnomad_genomes', 'gnomad_non_coding_constraint',
        'originalAltAlleles', 'primate_ai', 'splice_ai', 'topmed',
    ],
    GCNV_TYPE: ['interval', 'rg37_locus', 'rg37_locus_end', 'num_exon'],
    SV_TYPE: ['rg37_locus', 'rg37_locus_end', 'xpos'],
    MITO_TYPE: VARIANT_SELECT_FIELDS + ['mitomap', 'common_low_heteroplasmy',  'high_constraint_region'],
}

PARSED_HT_EXTS = {
    VARIANT_TYPE: 'interval_annotations',
    GCNV_TYPE: 'grouped',
    SV_TYPE: 'annotated',
}


def write_main_ht(file, data_type):
    ht = hl.read_table(f'gs://hail-backend-datasets/{file}.{PARSED_HT_EXTS[data_type]}.ht') \
        if data_type in PARSED_HT_EXTS else hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').rows()

    ht = ht.select_globals()
    ht = ht.select(*SELECT_FIELDS[data_type], **{k: v(ht) for k, v in ANNOTATIONS[data_type].items()})
    ht.write(f'gs://hail-backend-datasets/{file}.ht')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('data_type', choices=ANNOTATIONS.keys())
    args = p.parse_args()

    write_main_ht(args.file, args.data_type)