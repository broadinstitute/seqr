import gzip
from collections import defaultdict
import progressbar
import re
import StringIO

from xbrowse import Family, Individual
from xbrowse.core import constants

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


def slugify(s, separator='_', replace_dot=False):
    """Simplified, custom implementation of the functionality in the awesome-slugify python module.
    A custom approach was needed because awesome-slugify only supports one char as the separator, for example '-' or '_'
    but here we keep both '-' and '_', while replacing all other special chars with '_'.

    Args:
        s: string to slugify (eg. remove special chars)
        separator: the char to use in place of special characters
    Return:
        string with all characters except [a-Z\-_.] replaced with '_'
    """
    try:
        regexp = '[^a-zA-Z0-9\-_.]+' if not replace_dot else '[^a-zA-Z0-9\-_]+'
        words = re.split(regexp, s)
    except Exception as e:
        print("ERROR: string '%s' caused: %s" % (e, s))
        raise

    return separator.join(filter(None, words))


# make encoded values as human-readable as possible
ES_FIELD_NAME_ESCAPE_CHAR = '$'
ES_FIELD_NAME_BAD_LEADING_CHARS = set(['_', '-', '+', ES_FIELD_NAME_ESCAPE_CHAR])
ES_FIELD_NAME_SPECIAL_CHAR_MAP = {
    '.': '_$dot$_',
    ',': '_$comma$_',
    '#': '_$hash$_',
    '*': '_$star$_',
    '(': '_$lp$_',
    ')': '_$rp$_',
    '[': '_$lsb$_',
    ']': '_$rsb$_',
    '{': '_$lcb$_',
    '}': '_$rcb$_',
}


def _encode_name(s):
    """Applies a reversable encoding to the special chars in the given name or id string, and returns the result.
    Among other things, the encoded string is a valid elasticsearch or mongodb field name.

    See:
    https://discuss.elastic.co/t/special-characters-in-field-names/10658/2
    https://discuss.elastic.co/t/illegal-characters-in-elasticsearch-field-names/17196/2
    """
    field_name = StringIO.StringIO()
    for c in s:
        if c == ES_FIELD_NAME_ESCAPE_CHAR:
            field_name.write(2*ES_FIELD_NAME_ESCAPE_CHAR)
        elif c in ES_FIELD_NAME_SPECIAL_CHAR_MAP:
            field_name.write(ES_FIELD_NAME_SPECIAL_CHAR_MAP[c])  # encode the char
        else:
            field_name.write(c)  # write out the char as is

    field_name = field_name.getvalue()

    # escape 1st char if necessary
    if any(field_name.startswith(c) for c in ES_FIELD_NAME_BAD_LEADING_CHARS):
        return ES_FIELD_NAME_ESCAPE_CHAR + field_name
    else:
        return field_name


def _decode_name(s):
    """Decodes a name or id string that was encoded by #_encode_name(..) and returns the original string"""

    if s.startswith(ES_FIELD_NAME_ESCAPE_CHAR):
        s = s[1:]

    i = 0
    original_string = StringIO.StringIO()
    while i < len(s):
        current_string = s[i:]
        if current_string.startswith(2*ES_FIELD_NAME_ESCAPE_CHAR):
            original_string.write(ES_FIELD_NAME_ESCAPE_CHAR)
            i += 2
        else:
            for original_value, encoded_value in ES_FIELD_NAME_SPECIAL_CHAR_MAP.items():
                if current_string.startswith(encoded_value):
                    original_string.write(original_value)
                    i += len(encoded_value)
                    break
            else:
                original_string.write(s[i])
                i += 1

    return original_string.getvalue()

