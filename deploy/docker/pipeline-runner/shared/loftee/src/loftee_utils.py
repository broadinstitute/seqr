__author__ = 'konradjk'
from operator import itemgetter
import re
import sys

# Note that this is the current as of v81 with some included for backwards compatibility (VEP <= 75)
csq_order = ["transcript_ablation",
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
""]
csq_order_dict = dict(zip(csq_order, range(len(csq_order))))
rev_csq_order_dict = dict(zip(range(len(csq_order)), csq_order))


def worst_csq_index(csq_list):
    """
    Input list of consequences (e.g. ['frameshift_variant', 'missense_variant'])
    Return index of the worst annotation (In this case, index of 'frameshift_variant', so 4)
    Works well with csqs = 'non_coding_exon_variant&nc_transcript_variant' by worst_csq_index(csqs.split('&'))

    :param annnotation:
    :return most_severe_consequence_index:
    """
    if len(csq_list) == 0:
        return len(csq_order) - 1
    else:
        return min([csq_order_dict[ann] for ann in csq_list])


def worst_csq_from_list(csq_list):
    """
    Input list of consequences (e.g. ['frameshift_variant', 'missense_variant'])
    Return the worst annotation (In this case, 'frameshift_variant')
    Works well with csqs = 'non_coding_exon_variant&nc_transcript_variant' by worst_csq_from_list(csqs.split('&'))

    :param annnotation:
    :return most_severe_consequence:
    """
    return rev_csq_order_dict[worst_csq_index(csq_list)]


def worst_csq_from_csq(csq):
    """
    Input possibly &-filled csq string (e.g. 'non_coding_exon_variant&nc_transcript_variant')
    Return the worst annotation (In this case, 'non_coding_exon_variant')

    :param consequence:
    :return most_severe_consequence:
    """
    return rev_csq_order_dict[worst_csq_index(csq.split('&'))]


def order_vep_by_csq(annotation_list):
    output = sorted(annotation_list, cmp=lambda x, y: compare_two_consequences(x, y), key=itemgetter('Consequence'))
    for ann in output:
        ann['major_consequence'] = worst_csq_from_csq(ann['Consequence'])
    return output


def worst_csq_with_vep(annotation_list):
    """
    Takes list of VEP annotations [{'Consequence': 'frameshift', Feature: 'ENST'}, ...]
    Returns most severe annotation (as full VEP annotation [{'Consequence': 'frameshift', Feature: 'ENST'}])
    Also tacks on worst consequence for that annotation (i.e. worst_csq_from_csq)
    :param annotation_list:
    :return worst_annotation:
    """
    if len(annotation_list) == 0: return None
    worst = annotation_list[0]
    for annotation in annotation_list:
        if compare_two_consequences(annotation['Consequence'], worst['Consequence']) < 0:
            worst = annotation
        elif compare_two_consequences(annotation['Consequence'], worst['Consequence']) == 0 and annotation['CANONICAL'] == 'YES':
            worst = annotation
    worst['major_consequence'] = worst_csq_from_csq(worst['Consequence'])
    return worst


def worst_csq_with_vep_all(annotation_list):
    """
    Like worst_csq_with_vep, but returns annotation list for tied annotations
    Takes list of VEP annotations [{'Consequence': 'frameshift', Feature: 'ENST'}, ...]
    Returns most severe annotation (as full VEP annotation [{'Consequence': 'frameshift', Feature: 'ENST'}])
    Also tacks on worst consequence for that annotation (i.e. worst_csq_from_csq)
    :param annotation_list:
    :return worst_annotation:
    """
    if len(annotation_list) == 0: return []
    worst = [annotation_list[0]]
    for annotation in annotation_list:
        if compare_two_consequences(annotation['Consequence'], worst[0]['Consequence']) < 0:
            worst = [annotation]
        elif compare_two_consequences(annotation['Consequence'], worst[0]['Consequence']) == 0:
            worst.append(annotation)
    return worst


def compare_two_consequences(csq1, csq2):
    if csq_order_dict[worst_csq_from_csq(csq1)] < csq_order_dict[worst_csq_from_csq(csq2)]:
        return -1
    elif csq_order_dict[worst_csq_from_csq(csq1)] == csq_order_dict[worst_csq_from_csq(csq2)]:
        return 0
    return 1


def simplify_polyphen(polyphen_list):
    """
    Takes list of polyphen score/label pairs (e.g. ['probably_damaging(0.968)', 'benign(0.402)'])
    Returns worst (worst label and highest score) - in this case, 'probably_damaging(0.968)'
    """
    max_score = 0
    max_label = 'unknown'
    for polyphen in polyphen_list:
        label, score = polyphen.rstrip(')').split('(')
        if float(score) >= max_score and label != 'unknown':
            max_score = float(score)
            max_label = label
    return max_label, max_score


def simplify_sift(sift_list):
    """
    Takes list of SIFT score/label pairs (e.g. ['tolerated(0.26)', 'deleterious(0)'])
    Returns worst (worst label and highest score) - in this case, 'deleterious(0)'
    """
    max_score = 1.0
    max_label = 'tolerated'
    for sift in sift_list:
        label, score = sift.rstrip(')').split('(')
        if float(score) < max_score:
            max_score = float(score)
            max_label = label
    return max_label, max_score

POLYPHEN_SIFT_REGEX = re.compile('^[a-z\_]+\([0-9\.]+\)$', re.IGNORECASE)


def simplify_polyphen_sift(input_list, type):
    if len(input_list) == 0 or not all([POLYPHEN_SIFT_REGEX.match(x) for x in input_list]):
        return None
    if type.lower() == 'polyphen':
        return simplify_polyphen(input_list)
    elif type.lower() == 'sift':
        return simplify_sift(input_list)
    raise Exception('Type is not polyphen or sift')


def get_feature_from_annotation(annotation_list, key):
    """
    Takes list of annotation dicts and a key.
    Returns one value of key from annotation dicts (dangerously assuming there will be one unique value of key)
    """
    this_set = get_set_from_annotation(annotation_list, key)
    if len(this_set) > 1:
        print >> sys.stderr, "WARNING: Set has more than one entry. Set was %s" % this_set
    return list(this_set)[0]


def get_set_from_annotation(annotation_list, key):
    """
    Takes list of annotation dicts and a key.
    Returns a set of all values of that key
    """
    return set([x[key] for x in annotation_list])


def filter_annotation(annotation_list, key, value=None, filter=True):
    """
    Returns annotation list filtered to entries where _key_ is _value_
    Some pre-specified keys are available (canonical, lof)
    """
    if value is None:
        if key.lower() == 'canonical':
            key = 'CANONICAL'
            value = 'YES'
        if key.lower() == 'lof':
            key = 'LoF'
            value = 'HC'
    if filter:
        return [x for x in annotation_list if x[key] == value]
    else:
        return [x for x in annotation_list if x[key] != value]


def filter_annotation_list(annotation_list, key, value_list, filter=True):
    """
    Returns annotation list filtered to entries where _key_ is in _value_list_
    """
    if filter:
        return [x for x in annotation_list if x[key] in value_list]
    else:
        return [x for x in annotation_list if x[key] not in value_list]
