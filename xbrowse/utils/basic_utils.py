import gzip
from collections import defaultdict
import progressbar
import re

from xbrowse import constants
from xbrowse import Family, Individual


def family_from_indiv_id_list(indiv_id_list, project_id, family_id):
    indivs = [Individual({'project_id': project_id, 'family_id': family_id, 'indiv_id': indiv_id}) for indiv_id in indiv_id_list]
    family = Family({'project_id': project_id, 'family_id': family_id})
    for indiv in indivs:
        family.add_individual(indiv)
    return family


def combine_annot_groups(annot_dict, **kwargs):

    combiner = kwargs.get('combiner', sum)
    initial_val = kwargs.get('initial_val', 0)

    group_values = {group['slug']: initial_val for group in constants.ANNOTATION_GROUPS}

    for k, v in annot_dict.items():
        group = constants.ANNOTATION_GROUP_REVERSE_MAP[k]
        group_values[group] = combiner([group_values[group], v])

    return group_values


def get_gene_from_arg(arg, reference):
    """
    Return ensembl ID from arg, which can be ensembl id or gene id
    """
    if reference.is_valid_gene_id(arg):
        return arg
    elif reference.gene_id_from_symbol(arg):
        return reference.gene_id_from_symbol(arg)
    else:
        return None


def get_progressbar(maxval, title=None):
    widgets = [
        progressbar.Percentage(), ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
        progressbar.ETA()
    ]
    if title:
        widgets.insert(0, '%s: ' % title)
    p = progressbar.ProgressBar(widgets=widgets, maxval=maxval)
    p.start()
    return p


def family_variant_from_full_variant(variant, family):
    """
    Extract a family variant from full variant
    It's just a copy, with the following changes:
    -- All genotypes from non-family individuals are removed
    -- variant['alt_allele_count'] is updated to alt allele count in family indivs

    Note that I refactored this from copy.deepcopy for performance
    """

    new_genotypes = {}
    for indiv_id in family['individuals']:
        new_genotypes[indiv_id] = variant['genotypes'][indiv_id]

    new_variant = variant.copy()
    new_variant['genotypes'] = new_genotypes
    new_variant['alt_allele_count'] = get_alt_allele_count(new_variant)

    return new_variant


def clip_individuals_from_variant(variant, indiv_id_list):
    """
    Extract a family variant from full variant
    It's just a copy, with the following changes:
    -- All genotypes from non-family individuals are removed
    -- variant['alt_allele_count'] is updated to alt allele count in indiv_id_list

    Note that I refactored this from copy.deepcopy for performance
    """

    new_genotypes = {}
    for indiv_id in indiv_id_list:
        new_genotypes[indiv_id] = variant['genotypes'][indiv_id]

    new_variant = variant.copy()
    new_variant['genotypes'] = new_genotypes
    new_variant['alt_allele_count'] = get_alt_allele_count(new_variant)

    return new_variant


def get_alt_allele_count(variant):
    """
    Get alt allele count for a variant
    """
    aac = 0
    for indiv_id, genotype in variant.get_genotypes():
        if genotype.num_alt is not None:
            aac += genotype.num_alt
    return aac


def alt_allele_count_map(variant_list):
    """
    Gets a map of indiv_id -> alt allele count from the variants in variant_list
    TODO: can we use collections.counter?
    """
    aac_map = defaultdict(int)
    for variant in variant_list:
        for indiv_id, genotype in variant.get_genotypes():
            if genotype.num_alt:
                aac_map[indiv_id] += genotype.num_alt
    return aac_map


# TODO: move to reference
def get_gene_id_from_str(s, reference):
    """
    Given an arbitrary string s, see if you can use reference
    to get a gene ID (ensembl ID)
    """
    if reference.is_valid_gene_id(s):
        return s
    elif reference.get_gene_id_from_symbol(s.lower()):
        return reference.get_gene_id_from_symbol(s.lower())
    else:
        return None


def get_aaf(variant):
    """
    Get alt allele frequency from a variant
    TODO: consider sex chromosomes
    TODO: tests
    """
    num_ref, num_alt = 0,0
    for indiv_id, genotype in variant.get_genotypes():
        if genotype.num_alt == 0:
            num_ref += 2
        elif genotype.num_alt > 0:
            num_alt += genotype.num_alt
    return float(num_alt) / float(num_ref + num_alt)


def is_variant_relevant_for_individuals(variant, indiv_id_list):
    """
    """
    has_missing = False
    has_refref = False
    for indiv_id in indiv_id_list:
    # this catches missing or an alt allele
        num_alt = variant.get_genotype(indiv_id).num_alt
        if num_alt > 0:
            return True
        elif num_alt is None:
            has_missing = True
        elif num_alt == 0:
            has_refref = True
    if has_missing and has_refref:
        return True
    return False


class CompressedFile(file):
    def __init__(self, *args, **kwargs):
        file.__init__(self, *args, **kwargs)
        self.tell_progress = self.tell

def compressed_file(file_path):
    """
    Return handle to a file, whether compressed or not
    gzip.open() if file_path ends in .gz
    Otherwise basic file handle
    """
    if file_path.endswith('.gz'):
        f = gzip.open(file_path)
        f.tell_progress = f.fileobj.tell
        return f
    else:
        return CompressedFile(file_path)



def slugify(s, separator='_'):
    """Simplified, custom implementation of the functionality in the awesome-slugify python module.
    A custom approach was needed because awesome-slugify only supports one char as the separator, for example '-' or '_'
    but here we keep both '-' and '_', while replacing all other special chars with '_'.

    Args:
        s: string to slugify (eg. remove special chars)
        separator: the char to use in place of special characters
    Return:
        string with all characters except [a-Z\-_] replaced with '_'
    """

    words = re.split('[^a-zA-Z0-9\-_]+', s)
    return separator.join(filter(None, words))