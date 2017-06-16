from hail import *
from hail.utils import *
from hail.seqr import *

import sys

seqr_host = sys.argv[1]
print('seqr_host', seqr_host)

vds_path = sys.argv[2]
print('vds_path', vds_path)

hc = HailContext()

def escaped_export_expr(exprs):
    return ' , '.join(['{} = {}'.format(escape_identifier(e[0]), e[1])
                       for e in exprs])

def escape_sample_ids(vds):
    return vds.rename_samples({s: escape_identifier(s) for s in vds.sample_ids})

vexprs = escaped_export_expr([
    ('dataset_id', '"cohen"'),
    ('chrom', 'v.contig'),
    ('start', 'v.start'),
    ('end', 'v.start + v.ref.length - 1'),
    ('ref', 'v.ref'),
    ('alt', 'v.alt'),
    ('clinvar_clinsig', 'va.clinvar_clinsig'),
    ('clinvar_review_status', 'va.clinvar_review_status'),
    ('clinvar_inheritance_mode', 'va.clinvar_inheritance_mode'),
    ('clinvar_disease_mechanism', 'va.clinvar_disease_mechanism'),
    ('clinvar_gold_stars', 'va.clinvar_gold_stars'),
    ('clinvar_is_pathogenic', 'va.clinvar_is_pathogenic'),
    ('clinvar_is_conflicted', 'va.clinvar_is_conflicted'),
    ('vep_gene_id', 'va.vep_gene_id'),
    ('vep_transcript_id', 'va.vep_transcript_id'),
    ('vep_most_severe_consequence', 'va.vep_most_severe_consequence'),
    ('g1k_wgs_phase3_popmax_af', 'va.g1k_wgs_phase3_popmax_af'),
    ('g1k_wgs_phase3_popmax', 'va.g1k_wgs_phase3_popmax'),
    ('exac_v1_popmax', 'va.exac_v1_popmax'),
    ('twinsuk_af', 'va.twinsuk_af'),
    ('alspac_af', 'va.alspac_af'),
    ('esp65000_aa_af', 'va.esp65000_aa_af'),
    ('esp65000_ea_af', 'va.esp65000_ea_af'),
    ('dbnsfp_sift_pred', 'va.dbnsfp_sift_pred'),
    ('dbnsfp_polyphen2_hdiv_pred', 'va.dbnsfp_polyphen2_hdiv_pred'),
    ('dbnsfp_polyphen2_hvar_pred', 'va.dbnsfp_polyphen2_hvar_pred'),
    ('dbnsfp_lrt_pred', 'va.dbnsfp_lrt_pred'),
    ('dbnsfp_muttaster_pred', 'va.dbnsfp_muttaster_pred'),
    ('dbnsfp_mutassesor_pred', 'va.dbnsfp_mutassesor_pred'),
    ('dbnsfp_fathmm_pred', 'va.dbnsfp_fathmm_pred'),
    ('dbnsfp_provean_pred', 'va.dbnsfp_provean_pred'),
    ('dbnsfp_metasvm_pred', 'va.dbnsfp_metasvm_pred'),
    ('dbnsfp_metalr_pred', 'va.dbnsfp_metalr_pred'),
    ('dbnsfp_cadd_phred', 'va.dbnsfp_cadd_phred'),
    ('vep_consequences', 'va.vep_consequences'),
    ('clinvar_submitter', 'va.clinvar_submitter'),
    ('clinvar_trait', 'va.clinvar_trait'),
    ('clinvar_pmid', 'va.clinvar_pmid'),
    ('clinvar_age_of_onset', 'va.clinvar_age_of_onset'),
    ('clinvar_prevalence', 'va.clinvar_prevalence'),
    ('clinvar_origin', 'va.clinvar_origin'),
    ('clinvar_xrefs', 'va.clinvar_xrefs')])

gexprs = escaped_export_expr([
    ('num_alt', 'g.nNonRefAlleles'),
    ('gq', 'g.gq'),
    ('ab', 'let s = g.ad.sum in g.ad[0] / s'),
    ('dp', 'g.dp')])

vds = hc.read(vds_path)

print(vds.variant_schema)
print(vds.global_schema)
print(vds.sample_schema)

cass_kt = (escape_sample_ids(vds)
           .make_table(vexprs, gexprs, separator='__'))

cass_kt.export_cassandra(seqr_host, 'seqr', 'seqr', rate = 5000 / 5, port = 30001)
