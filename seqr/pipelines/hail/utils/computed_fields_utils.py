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

# hail Dict expression that maps each CONSEQUENCE_TERM to it's rank in the list
CONSEQUENCE_TERM_RANKS = map(str, range(len(CONSEQUENCE_TERMS)))
CONSEQUENCE_TERM_RANK_LOOKUP = (
    "Dict(%s, %s)" % (CONSEQUENCE_TERMS, CONSEQUENCE_TERM_RANKS)
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

    so that the 1st array entry will be for the coding, most-severe, canonical transcript (assuming
    one exists).

    Also, for each transcript in the array, computes these additional fields:
        hgnc_id: converts type to String
        domains: converts Array[Struct] to string of comma-separated domain names
        hgvs: set to hgvsp is it exists, or else hgvsc. TODO needs more work to match gnomAD browser logic.
        major_consequence: set to most severe consequence for that transcript (
            VEP sometimes provides multiple consequences for a single transcript)
        major_consequence_rank: major_consequence rank based on VEP SO ontology (most severe = 1)
            (see http://www.ensembl.org/info/genome/variation/predicted_data.html)
        category: set to one of: "lof", "missense", "synonymous", "other" based on the value of major_consequence.
    """

    return """
    let CONSEQUENCE_TERM_RANK_LOOKUP = %(CONSEQUENCE_TERM_RANK_LOOKUP)s in
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
                            c.consequence_terms.toArray().sortBy(t => CONSEQUENCE_TERM_RANK_LOOKUP.get(t).toInt())[0]
                        else
                            NA:String
                })
        ).map(c => merge(c, {
                major_consequence_rank: CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence).toInt(),
                category:
                    if(CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_RANK_LOOKUP.get("frameshift_variant").toInt())
                        "lof"
                    else if(CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_RANK_LOOKUP.get("missense_variant").toInt())
                        "missense"
                    else if(CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence).toInt() <= CONSEQUENCE_TERM_RANK_LOOKUP.get("synonymous_variant").toInt())
                        "synonymous"
                    else
                        "other"
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


def get_expr_for_worst_transcript_consequence_annotations_struct(
        vep_sorted_transcript_consequences_root="va.vep.sorted_transcript_consequences"):
    """Retrieves the top-ranked transcript annotation based on the ranking computed by
    get_expr_for_vep_sorted_transcript_consequences_array(..)
    """

    return """
    let NA_type = NA:Struct{
        amino_acids:String,
        biotype:String,
        canonical:Int,
        cdna_start:Int,
        cdna_end:Int,
        codons:String,
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
        major_consequence_rank:Int,
        category:String} in
    if( %(vep_sorted_transcript_consequences_root)s.length == 0 )
        NA_type
    else
        select(%(vep_sorted_transcript_consequences_root)s[0],
            amino_acids,
            biotype,
            canonical,
            cdna_start,
            cdna_end,
            codons,
            distance,
            exon,
            gene_id,
            gene_symbol,
            gene_symbol_source,
            hgvsc,
            hgvsp,
            lof,
            lof_flags,
            lof_filter,
            lof_info,
            protein_id,
            transcript_id,
            hgnc_id,
            domains,
            hgvs,
            major_consequence,
            major_consequence_rank,
            category
        )
    """ % locals()


def get_expr_for_contig(field_prefix="v."):
    """Normalized contig name"""
    return field_prefix+'contig.replace("chr", "")'

def get_expr_for_start_pos():
    return 'v.start'

def get_expr_for_ref_allele():
    return 'v.ref'

def get_expr_for_alt_allele():
    return 'v.alt'

def get_expr_for_orig_alt_alleles_set():
    """Compute an array of variant ids for each alt allele"""
    contig_expr = get_expr_for_contig()
    return 'v.altAlleles.map( a => %(contig_expr)s + "-" + v.start + "-" + v.ref + "-" + a.alt ).toSet' % locals()


def get_expr_for_variant_id():
    contig_expr = get_expr_for_contig()
    return '%(contig_expr)s + "-" + v.start + "-" + v.ref + "-" + v.alt' % locals()


def get_expr_for_contig_number(field_prefix="v."):
    """Convert contig name to contig number"""

    contig_expr = get_expr_for_contig(field_prefix)
    return """
        let contig = %(contig_expr)s in
            if(contig == "X") 23
            else if (contig == "Y") 24
            else if (contig[0] == "M") 25
            else contig.toInt()
    """ % locals()


def get_expr_for_xpos(field_prefix="v.", pos_field="start"):
    """Genomic position represented as a single number = contig_number * 10**9 + position.
    This represents chrom:pos more compactly and allows for easier sorting.
    """
    contig_number_expr = get_expr_for_contig_number(field_prefix)
    return """
    let contig_number = %(contig_number_expr)s and pos = %(field_prefix)s%(pos_field)s in
        1000000000 * contig_number.toLong() + pos
    """ % locals()


def get_expr_for_end_pos(field_prefix="v.", pos_field="start", ref_field="ref"):
    """Compute the end position based on start position and ref allele length"""
    return "%(field_prefix)s%(pos_field)s + %(field_prefix)s%(ref_field)s.length - 1" % locals()


def copy_field(vds, dest_field="va.pos", source_field="v.start"):
    """Copy a field from one place in the schema to another"""
    return vds.annotate_variants_expr(
        '%(root)s = %(source_field)s' % locals()
    )



