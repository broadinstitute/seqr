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


def add_vep_gene_ids_set(vds, root="va.vep.gene_ids"):
    return vds.annotate_variants_expr(
        '%(root)s = va.vep.transcript_consequences.map( x => x.gene_id ).toSet' % locals()
    )


def add_vep_transcript_ids_set(vds, root="va.vep.transcript_ids"):
    return vds.annotate_variants_expr(
        '%(root)s = va.vep.transcript_consequences.map( x => x.transcript_id ).toSet' % locals()
    )


def add_vep_consequence_terms_set(vds, root="va.vep.consequence_terms"):
    return vds.annotate_variants_expr(
        '%(root)s = va.vep.transcript_consequences.map( x => x.consequence_terms ).flatten().toSet' % locals()
    )


def add_vep_sorted_transcript_consequences(vds, root="va.vep.sorted_transcript_consequences"):
    """Sort transcripts by 3 properties:

        1. coding > non-coding
        2. transcript consequence severity
        3. canonical > non-canonical

    So that the 1st entry in the Array will be for the coding, most-severe, canonical transcript
    (assuming such a transcript exists).
    """

    return vds.annotate_variants_expr("""
        %(root)s = let CONSEQUENCE_TERM_ORDER = %(CONSEQUENCE_TERM_ORDER)s in
            va.vep.transcript_consequences.map(
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
                c => merge(drop(c, hgnc_id), {
                        hgvs:
                            orElse(c.hgvsp, c.hgvsc),
                        major_consequence: if( c.consequence_terms.size() > 0)
                                c.consequence_terms.toArray().sortBy(t => CONSEQUENCE_TERM_ORDER.get(t).toInt())[0]
                            else
                                NA:String,
                        hgnc_id: str(c.hgnc_id)
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
                is_most_severe=c.consequence_terms.toSet.contains(va.vep.most_severe_consequence) and
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
        """ % dict(locals().items()+globals().items()))


def add_worst_transcript_consequence_annotations(vds, root="va", sorted_transcript_consequences="va.vep.sorted_transcript_consequences"):

    return vds.annotate_variants_expr("""
        %(root)s = merge(
            %(root)s,
            let NA_type = NA:Struct{
                amino_acids:String,
                biotype:String,
                canonical:Int,
                cdna_start:Int,
                cdna_end:Int,
                codons:String,
                consequence_terms:Array[String],
                distance:Int,
                domains:Array[Struct{db:String,name:String}],
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
                hgvs:String,
                major_consequence:String,
                hgnc_id:String,
                category:String} in
            if( %(sorted_transcript_consequences)s.length == 0 )
                NA_type
            else
                %(sorted_transcript_consequences)s[0]
        )
    """ % locals())



def add_gnomad_consequences(vds):
    # adds the fields from https://github.com/macarthur-lab/gnomad_browser/blob/master/utils.py#L70
    pass

def convert_to_json_string(vds, root="va.vep.sortedTranscriptConsequences"):
    return vds.annotate_variants_expr("%(root)s = json(%(root)s)" % locals())

def save_alt_alleles_before_splitting(vds, root="va.original_alt_alleles"):
    return vds.annotate_variants_expr(
        '%(root)s = v.altAlleles.map( a => v.contig + "-" + v.start + "-" + v.ref + "-" + a.alt ).toSet' % locals()
    )

def add_variant_id(vds, root="va.variantId"):
    return vds.annotate_variants_expr(
        '%(root)s = v.contig + "-" + v.start + "-" + v.ref + "-" + v.alt' % locals()
    )


def add_xpos(vds, root="va.xpos", pos_field="v.start"):
    return vds.annotate_variants_expr(
        '%(root)s = 1000000000 * ('
        '   if(v.contig == "X") 23 '
        '   else if (v.contig == "Y") 24 '
        '   else if (v.contig[0] == "M") 25 '
        '   else v.contig.toInt()'
        ') + %(pos_field)s' % locals()
    )


def copy_field(vds, root="va.pos", source_field="v.start"):
    return vds.annotate_variants_expr(
        '%(root)s = %(source_field)s' % locals()
    )


def add_end_pos(vds, root="va.end"):
    return vds.annotate_variants_expr(
        '%(root)s = v.start + v.ref.length - 1' % locals()
    )

