from hail import *
from hail.utils import *
from hail.seqr import *

import sys

solr_host = sys.argv[1]
print('solr_host', solr_host)

vds_path = sys.argv[2]
print('vds_path', vds_path)

hc = HailContext()

def escaped_export_expr(exprs):
    return ' , '.join(['{} = {}'.format(escape_identifier(e[0]), e[1])
                       for e in exprs])

def escape_sample_ids(vds):
    return vds.rename_samples({s: escape_identifier(s) for s in vds.sample_ids})

def make_solr_keytable(vds, vexprs, gexprs):
    kt = vds.make_table(escaped_export_expr(vexprs),
                        escaped_export_expr(gexprs),
                        separator='__')

    fa = {escape_identifier(e[0]): e[2]
           for e in vexprs}
    
    gfa = {s + '__' + escape_identifier(e[0]): e[2]
           for e in gexprs
           for s in vds.sample_ids}
    fa.update(gfa)
    
    return (kt, fa)

stored = {'docValues': False}
indexed = {'stored': False, 'docValues': False}

vds = hc.read(vds_path)

print(vds.variant_schema)
print(vds.global_schema)
print(vds.sample_schema)

(solr_kt, field_attrs) = make_solr_keytable(
    escape_sample_ids(vds),
    [('dataset_id', '"cohen"', stored),
     ('chrom', 'v.contig', stored),
     ('start', 'v.start', stored),
     ('ref', 'v.ref', stored),
     ('alt', 'v.alt', stored),
     ('end', 'v.start + v.ref.length - 1', indexed),
     ('clinvar_clinsig', 'va.clinvar_clinsig', indexed),
     ('clinvar_review_status', 'va.clinvar_review_status', indexed),
     ('clinvar_inheritance_mode', 'va.clinvar_inheritance_mode', indexed),
     ('clinvar_disease_mechanism', 'va.clinvar_disease_mechanism', indexed),
     ('clinvar_gold_stars', 'va.clinvar_gold_stars', indexed),
     ('clinvar_is_pathogenic', 'va.clinvar_is_pathogenic', indexed),
     ('clinvar_is_conflicted', 'va.clinvar_is_conflicted', indexed),
     ('vep_gene_id', 'va.vep_gene_id', indexed),
     ('vep_transcript_id', 'va.vep_transcript_id', indexed),
     ('vep_most_severe_consequence', 'va.vep_most_severe_consequence', indexed),
     ('g1k_wgs_phase3_popmax_af', 'va.g1k_wgs_phase3_popmax_af', indexed),
     ('g1k_wgs_phase3_popmax', 'va.g1k_wgs_phase3_popmax', indexed),
     ('exac_v1_popmax', 'va.exac_v1_popmax', indexed),
     ('twinsuk_af', 'va.twinsuk_af', indexed),
     ('alspac_af', 'va.alspac_af', indexed),
     ('esp65000_aa_af', 'va.esp65000_aa_af', indexed),
     ('esp65000_ea_af', 'va.esp65000_ea_af', indexed),
     ('dbnsfp_sift_pred', 'va.dbnsfp_sift_pred', indexed),
     ('dbnsfp_polyphen2_hdiv_pred', 'va.dbnsfp_polyphen2_hdiv_pred', indexed),
     ('dbnsfp_polyphen2_hvar_pred', 'va.dbnsfp_polyphen2_hvar_pred', indexed),
     ('dbnsfp_lrt_pred', 'va.dbnsfp_lrt_pred', indexed),
     ('dbnsfp_muttaster_pred', 'va.dbnsfp_muttaster_pred', indexed),
     ('dbnsfp_mutassesor_pred', 'va.dbnsfp_mutassesor_pred', indexed),
     ('dbnsfp_fathmm_pred', 'va.dbnsfp_fathmm_pred', indexed),
     ('dbnsfp_provean_pred', 'va.dbnsfp_provean_pred', indexed),
     ('dbnsfp_metasvm_pred', 'va.dbnsfp_metasvm_pred', indexed),
     ('dbnsfp_metalr_pred', 'va.dbnsfp_metalr_pred', indexed),
     ('dbnsfp_cadd_phred', 'va.dbnsfp_cadd_phred', indexed),
     ('vep_consequences', 'va.vep_consequences', indexed),
     ('clinvar_submitter', 'va.clinvar_submitter', indexed),
     ('clinvar_trait', 'va.clinvar_trait', indexed),
     ('clinvar_pmid', 'va.clinvar_pmid', indexed),
     ('clinvar_age_of_onset', 'va.clinvar_age_of_onset', indexed),
     ('clinvar_prevalence', 'va.clinvar_prevalence', indexed),
     ('clinvar_origin', 'va.clinvar_origin', indexed),
     ('clinvar_xrefs', 'va.clinvar_xrefs', indexed)],
    [('num_alt', 'let n = g.nNonRefAlleles.orElse(-1) in if (n != 0) n else NA: Int', indexed),
     ('gq', 'if (g.nNonRefAlleles > 0) g.gq else NA: Int', indexed),
     ('ab', 'if (g.nNonRefAlleles > 0) g.ad[0] / g.ad.sum else NA: Double', indexed),
     ('dp', 'if (g.nNonRefAlleles > 0) g.dp else NA: Int', indexed)])

solr_kt.export_solr(solr_host + ':31002', 'seqr_noref', field_attrs)
