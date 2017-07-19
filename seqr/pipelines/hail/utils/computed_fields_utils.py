from pprint import pprint

CONSEQUENCE_TERMS = [
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
]

CONSEQUENCE_TERM_ORDER = (
    "Dict(%s, %s)" % (
        CONSEQUENCE_TERMS,
        map(str, range(len(CONSEQUENCE_TERMS)))
    )
).replace("'", '"')


def get_expr_for_vep_gene_ids_set(vep_root="va.vep"):
    return "%(vep_root)s.transcript_consequences.map( x => x.gene_id ).toSet" % locals()


def get_expr_for_vep_transcript_ids_set(vep_root="va.vep"):
    return "%(vep_root)s.transcript_consequences.map( x => x.transcript_id ).toSet" % locals()


def get_expr_for_vep_consequence_terms_set(vep_root="va.vep"):
    return "%(vep_root)s.transcript_consequences.map( x => x.consequence_terms ).flatten().toSet" % locals()


def get_expr_for_vep_sorted_transcript_consequences_array(vep_root="va.vep"):
    """Sort transcripts by 3 properties:

        1. coding > non-coding
        2. transcript consequence severity
        3. canonical > non-canonical

    So that the 1st entry in the Array will be for the coding, most-severe, canonical transcript
    (assuming such a transcript exists).
    """

    return """
    let CONSEQUENCE_TERM_ORDER = %(CONSEQUENCE_TERM_ORDER)s in
        %(vep_root)s.transcript_consequences.map(
            c => select(c,
                amino_acids,
                biotype,
                canonical,
                cdna_start,
                cdna_end,
                codons,
                consequence_terms,
                distance,
                domains,
                exon,
                gene_id,
                transcript_id,
                protein_id,
                gene_symbol,
                gene_symbol_source,
                hgnc_id,
                hgvsc,
                hgvsp,
                lof,
                lof_flags,
                lof_filter,
                lof_info)
        ).map(
            c => merge(
                drop(c, hgnc_id, domains),
                {
                    hgnc_id: str(c.hgnc_id),
                    domains: c.domains.map( domain => domain.name ).mkString(","),
                    hgvs: orElse(c.hgvsp, c.hgvsc),
                    major_consequence: if( c.consequence_terms.size() > 0)
                            c.consequence_terms.toArray().sortBy(t => CONSEQUENCE_TERM_ORDER.get(t).toInt())[0]
                        else
                            NA:String
                })
        ).map(c =>
            let CONSEQUENCE_TERM_ORDER = %(CONSEQUENCE_TERM_ORDER)s in
            merge(c, {
                category:
                    if(CONSEQUENCE_TERM_ORDER.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_ORDER.get("frameshift_variant").toInt())
                        "lof_variant"
                    else if(CONSEQUENCE_TERM_ORDER.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_ORDER.get("missense_variant").toInt())
                        "missense_variant"
                    else if(CONSEQUENCE_TERM_ORDER.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_ORDER.get("synonymous_variant").toInt())
                        "synonymous_variant"
                    else
                        "other_variant"
            })
        ).sortBy(c => let
            is_coding=(c.biotype == "protein_coding") and
            is_most_severe=c.consequence_terms.toSet.contains(%(vep_root)s.most_severe_consequence) and
            is_canonical=(c.canonical==1) in

            if(is_coding)
                if(is_most_severe)
                    if(is_canonical)  1  else  2
                else
                    if(is_canonical)  3  else  4
            else
                if(is_most_severe)
                    if(is_canonical)  5  else  6
                else
                    if(is_canonical)  7  else  8
        )
    """ % dict(locals().items()+globals().items())


def get_expr_for_worst_transcript_consequence_annotations_struct(vep_sorted_transcript_consequences_root="va.vep.sorted_transcript_consequences"):

    return """
    let NA_type = NA:Struct{
        amino_acids:String,
        biotype:String,
        canonical:Int,
        cdna_start:Int,
        cdna_end:Int,
        codons:String,
        consequence_terms:Array[String],
        distance:Int,
        exon:String,
        gene_id:String,
        gene_symbol:String,
        gene_symbol_source:String,
        hgvsc:String,
        hgvsp:String,
        lof:String,
        lof_flags:String,
        lof_filter:String,
        lof_info:String,
        protein_id:String,
        transcript_id:String,
        hgnc_id:String,
        domains:String,
        hgvs:String,
        major_consequence:String,
        category:String} in
    if( %(vep_sorted_transcript_consequences_root)s.length == 0 )
        NA_type
    else
        %(vep_sorted_transcript_consequences_root)s[0]
    """ % locals()



#def get_gnomad_consequences_struct(vds):
#    # compute the fields from https://github.com/macarthur-lab/gnomad_browser/blob/master/utils.py#L70
#    pass


def get_expr_for_orig_alt_alleles_set():
    return 'v.altAlleles.map( a => v.contig + "-" + v.start + "-" + v.ref + "-" + a.alt ).toSet' % locals()


def get_expr_for_variant_id():
    return 'v.contig + "-" + v.start + "-" + v.ref + "-" + v.alt' % locals()


def get_expr_for_xpos(field_prefix="v.", contig_field="contig", pos_field="start"):
    return (
        '1000000000 * ( '
        '   if(%(field_prefix)s%(contig_field)s == "X") 23'
        '   else if (%(field_prefix)s%(contig_field)s == "Y") 24'
        '   else if (%(field_prefix)s%(contig_field)s[0] == "M") 25'
        '   else %(field_prefix)s%(contig_field)s.toInt()'
        ') + %(field_prefix)s%(pos_field)s') % locals()


def get_expr_for_end_pos(field_prefix="v.", pos_field="start", ref_field="ref"):
    return "%(field_prefix)s%(pos_field)s + %(field_prefix)s%(ref_field)s.length - 1" % locals()

def copy_field(vds, dest_field="va.pos", source_field="v.start"):
    return vds.annotate_variants_expr(
        '%(root)s = %(source_field)s' % locals()
    )



