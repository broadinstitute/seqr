SO_SEVERITY_ORDER = [
    'transcript_ablation',
    'splice_donor_variant',
    "splice_acceptor_variant",
    'stop_gained',
    'frameshift_variant',
    'stop_lost',
    'initiator_codon_variant',
    'inframe_insertion',
    'inframe_deletion',
    'missense_variant',
    'transcript_amplification',
    'splice_region_variant',
    'incomplete_terminal_codon_variant',
    'synonymous_variant',
    'stop_retained_variant',
    'coding_sequence_variant',
    'mature_miRNA_variant',
    '5_prime_UTR_variant',
    '3_prime_UTR_variant',
    'intron_variant',
    'NMD_transcript_variant',
    'non_coding_exon_variant',
    'nc_transcript_variant',
    'upstream_gene_variant',
    'downstream_gene_variant',
    'TFBS_ablation',
    'TFBS_amplification',
    'TF_binding_site_variant',
    'regulatory_region_variant',
    'regulatory_region_ablation',
    'regulatory_region_amplification',
    'feature_elongation',
    'feature_truncation',
    'intergenic_variant',
    ''
]

SO_SEVERITY_ORDER_POS = { t: i for i, t in enumerate(SO_SEVERITY_ORDER) }
CODING_POS_CUTOFF = SO_SEVERITY_ORDER_POS['coding_sequence_variant']

NUM_SO_TERMS = len(SO_SEVERITY_ORDER)


def get_worst_vep_annotation(annot_list):
    """
    From a list of SO terms, return the worst
    Don't check that all items in annot_list are actually valid SO terms
    """
    annots = set(annot_list)
    for annot in SO_SEVERITY_ORDER:
        if annot in annots:
            return annot
    raise Exception('No items in annot_list are in SO_SEVERITY_ORDER')


def get_worst_vep_annotation_index(vep_annotation, gene_id=None):
    """
    Returns index of which VEP annotation is worst (zero-indexed)
    Exception if no vep annotation for some reason

    if you want the index of worst annotation for a given gene, pass gene_id
    gene_id is None implies the worst global annotation

    """

    num_annotations = len(vep_annotation)
    if num_annotations == 0:
        print 'Warning: no VEP annnotation'
        return None

    worst_value = 1000
    worst_index = -1
    for i in range(num_annotations):

        if gene_id and vep_annotation[i]['gene'] != gene_id: continue

        annot = vep_annotation[i]['consequence']

        try:
            pos = SO_SEVERITY_ORDER.index(annot)

            # hack: this is to deprioritize noncoding and nonsense mediated decay transcripts
            if vep_annotation[i]['is_nc']:
                pos += NUM_SO_TERMS
            if vep_annotation[i]['is_nmd']:
                pos += 2*NUM_SO_TERMS

        except ValueError:
            print 'Warning: no VEP ordering for %s' % annot
            return None

        if pos < worst_value:
            worst_index = i
            worst_value = pos

    return worst_index


def get_gene_ids(vep_annotation):
    """
    Gets the set of gene ids this variant is attached to
    Empty list if no annotations
    """
    return list(set([annotation['gene'] for annotation in vep_annotation]))


def is_coding_annotation(annotation):
    """
    Does this annotation impact coding?
    """
    return SO_SEVERITY_ORDER_POS[annotation['consequence']] <= CODING_POS_CUTOFF


def get_coding_gene_ids(vep_annotation):
    """
    Set of gene IDs that this is a coding variant for
    Still included even if is_nmd or is_nc
    Empty list if no annotations
    """
    return list(set([annotation['gene'] for annotation in vep_annotation if is_coding_annotation(annotation) ]))

