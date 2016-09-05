#
# This file contains all the various operations we do on VCF files directly
#

import sys
import gzip
from xbrowse.utils import slugify
import vcf as pyvcf
from xbrowse.utils import compressed_file

from xbrowse import genomeloc
from xbrowse import family_utils
from xbrowse.core.variants import Variant, Genotype
from xbrowse.utils.minirep import get_minimal_representation


def get_ids_from_vcf_path(vcf_file_path):
    if vcf_file_path.endswith('.gz'):
        f = gzip.open(vcf_file_path)
    else:
        f = open(vcf_file_path)
    return get_ids_from_vcf(f)


def get_ids_from_vcf(vcf_file):
    """
    Get the individuals in a VCF
    """
    for _line in vcf_file:
        line = _line.strip('\n')
        if line.startswith('#CHROM'):
            vcf_headers = get_vcf_headers(line)
            return map(slugify, vcf_headers[9:])


def get_missing_ids_from_vcf(indiv_id_list, vcf_file):
    """
    For ids in indiv_id_list, return list of missing
    If none missing, returns []
    """
    ids_in_vcf = get_ids_from_vcf_path(vcf_file)
    missing = [i for i in indiv_id_list if i not in ids_in_vcf]
    return missing


# TODO: do we want this? where should it live?
# TEST
def get_extra_indivs_in_vcf(families, vcf_file):
    """
    Matches the individuals in families with vcf_file
    Return list of individuals from VCF that are not present in vcf_file
    Note that an indiv_id needs only be unique within a family - an id from the vcf
    can be in multiple families and won't be treated any different than if it were in one
    """

    extra_indivs = set(get_ids_from_vcf_path(vcf_file))

    for family in families:
        for indiv_id in family['individuals'].keys():
            extra_indivs.discard(indiv_id)

    return extra_indivs


def get_cohort_from_vcf(project_id, family_id, vcf_file, ids_in_cohort=None):
    """
    Gets a cohort from a vcf file, reading the identifiers in the VCF
    # TODO: shouldn't need project ID
    # TODO: should replace with make_cohort_from_ids in cohort_utils.py
    """
    if ids_in_cohort is not None:
        indiv_ids = ids_in_cohort
    else:
        indiv_ids = get_ids_from_vcf_path(vcf_file)

    family = family_utils.make_family(project_id, family_id)
    family['is_cohort'] = True

    for i in indiv_ids:
        family['individuals'][i] = family_utils.make_indiv(i, family_id=family_id, affected='A')

    return family


def get_vcf_headers(header_line):

    if not header_line.startswith('#'):
        raise Exception

    return header_line.strip('#').split('\t')


def get_variants_from_vcf_fields(vcf_fields):
    """
    return a *list* of variants that are taken from vcf_fields
    One for each alt allele
    """

    num_alt_alleles = len(vcf_fields[4].split(','))
    variants = []
    for i in range(num_alt_alleles):
        variant = get_variant_from_vcf_fields(vcf_fields, i)
        if variant is not None:
            variants.append(variant)

    return variants


def get_variant_from_vcf_fields(vcf_fields, alt_allele_pos):
    """
    Get a basic variant from vcf_fields, for allele given by alt_allele_pos
    """

    chrom = vcf_fields[0] if 'chr' in vcf_fields[0] else 'chr' + vcf_fields[0]
    pos = int(vcf_fields[1])

    # if we can't get a genomic location, just ignore it and print a message humans will ignore too
    # obviously need a better way to approach this
    if not genomeloc.valid_pos(chrom, pos):
        print "ERROR: could not figure out coordinates for %s:%d...maybe a nonstandard chromosome?" % (chrom, pos)
        return None

    ref = vcf_fields[3]
    orig_alt_alleles = vcf_fields[4].split(',')
    alt = orig_alt_alleles[alt_allele_pos]

    xpos = genomeloc.get_single_location(chrom, pos)
    xpos, ref, alt = get_minimal_representation(xpos, ref, alt)

    variant = Variant(xpos, ref, alt)
    variant.set_extra('alt_allele_pos', alt_allele_pos)
    variant.set_extra('orig_alt_alleles', orig_alt_alleles)

    if vcf_fields[2] and vcf_fields[2] != '.':
        variant.vcf_id = vcf_fields[2]

    return variant


def add_vcf_info_to_variant(vcf_info_field, variant, meta_fields=None):
    """
    Adds VCF INFO field to a Variant as meta
    Fields are dict of string -> string; no other parsing

    Default is to add all info fields; can restrict to a subset with meta_fields

    case is preserved from the VCF fields, though if you are reading
    this I find it really annoying that everything there is capitalized
    """
    if meta_fields is None:
        meta_fields = []

    for meta in vcf_info_field.split(';'):

        try:
            k, v = meta.split('=')
        except ValueError:
            # TODO: what should we do with these? Need to check VCF spec
            continue

        # ignore if subsetting and this key doesn't make it
        if k not in meta_fields:
            continue

        variant.extras[k] = v


# TODO: what is allele balance for a triallelic variant with AD of "1/1/1"
def get_allele_balance(genotype_dict, alt_allele_pos):
    """
    Returns the allele balance for a genotype;
    Or '.' if ab does not apply
    """

    # can't compute ab without ad
    if genotype_dict['extras'].get('ad') is None or genotype_dict['extras']['ad'] == '.':
        return None

    ad_fields = [int(s) for s in genotype_dict['extras']['ad'].split(',')]

    # TODO: should we still compute AD for
    if len(ad_fields) == 1: return '.'

    # if multiallelic variant, but ad only has two parts, assume second part is alt allele
    if alt_allele_pos > 0 and len(ad_fields) == 2:
        ref_reads = ad_fields[0]
        alt_reads = ad_fields[1]

    # otherwise process the normal way
    else:
        ref_reads = ad_fields[0]
        alt_reads = ad_fields[alt_allele_pos + 1]

    if alt_reads + ref_reads == 0:
        return None

    return float(alt_reads) / (float(alt_reads) + ref_reads)


def get_num_alt_from_str(gq_str, alt_allele_pos):
    """
    gq_str is the value of the GT attr; return the number of alt alleles
    """
    if gq_str == '.' or gq_str == './.':
        return None

    a1, a2 = gq_str.split('/')

    num_alt_alleles = 0
    if a1 == '.' or a2 == '.':
        num_alt_alleles = None
    else:
        if int(a1) == alt_allele_pos + 1:
            num_alt_alleles += 1
        if int(a2) == alt_allele_pos + 1:
            num_alt_alleles += 1

    return num_alt_alleles


def get_genotype_from_str_without_meta(geno_str, alt_allele_pos):

    genotype = dict(
        num_alt=-1
    )

    if geno_str == '.': return genotype
    elif geno_str == './.': return genotype

    genotype_field = geno_str.split(':')[0]

    # assume GT field is always first
    genotype['num_alt'] = get_num_alt_from_str(genotype_field, alt_allele_pos)

    return genotype


def get_genotype_from_str(geno_str, format_map, alt_allele_pos, allele_position_map, vcf_filter=None):
    """
    Get genotype dict from geno_str
    format_map is just a map of 'ad' -> 4
    """

    extras = {
        'dp': None,  # string; DP field in VCF
        'pl': None,  # string; PL field in VCF
        'ad': None,  # string; the AD field in VCF
    }

    geno_dict = dict(
        alleles=[],
        num_alt=None,
        gq=None,
        ab=None,
        filter=vcf_filter,
        extras=extras,
    )

    if geno_str == '.' or geno_str == './.':
        return Genotype(**geno_dict)

    geno_fields = geno_str.split(':')

    # assume GT field is always first
    num_alt = get_num_alt_from_str(geno_fields[0], alt_allele_pos)
    geno_dict['num_alt'] = num_alt
    if geno_dict['num_alt'] is not None:
        a1, a2 = geno_fields[0].split('/')
        if a1 in allele_position_map and a2 in allele_position_map:
            alleles = [allele_position_map[a1], allele_position_map[a2]]
            geno_dict['alleles'] = alleles
        else:
            sys.stdout.write("WARNING: Could not parse genotype from string: %s with format: %s. Allele_position_map: %s" % (geno_str, format_map, allele_position_map))


    num_fields = len(geno_fields)
    for k, pos in format_map.items():

        # accommodate the fact that VCF can skip trailing genotype fields
        if pos >= num_fields:
            continue

        if k == 'gq':
            try:
                geno_dict['gq'] = float(geno_fields[pos])
            except ValueError:
                pass
        else:
            extras[k] = geno_fields[pos]

    geno_dict['ab'] = get_allele_balance(geno_dict, alt_allele_pos)

    return Genotype(**geno_dict)


def get_format_map(format_str):
    """
    Get a map of key -> pos from the VCF format
    Note that I treat all format strings lowercase; not sure why
    """
    formats = {}

    for i, item in enumerate(format_str.split(':')):
        if item == 'AD':
            formats['ad'] = i
        elif item == 'DP':
            formats['dp'] = i
        elif item == 'GQ':
            formats['gq'] = i
        elif item == 'PL':
            formats['pl'] = i

    return formats


def get_allele_position_map(ref_allele, alt_allele_str):
    """
    Get map of allele position -> allele
    allele position is just the string from the VCF
    For example, '0' -> 'A', '1' -> 'T', '2' -> 'C' if ref is A and alt is T/C
    Note that this is *not* the same as alt_allele_pos, which shows up around the code but will be deprecated
    """
    d = {
        '0': ref_allele
    }
    for i, allele in enumerate(alt_allele_str.split(',')):
        d[str(i+1)] = allele
    return d


def set_genotypes_from_vcf_fields(vcf_fields, variant, alt_allele_pos, vcf_header_fields, genotype_meta=True, indivs_to_include=None, vcf_id_map=None):
    """
    if variant is a basic variants, initialize its genotypes from vcf_fields
    vcf_header_fields is just a list of the headers in the vcf
    (with the # stripped of the #CHROM in the first column)

    vcf_id_map: dict of [ID in the VCF file] -> [Individual ID]
    """
    num_columns = len(vcf_fields)
    if num_columns != len(vcf_header_fields):
        raise Exception("Wrong number of columns")

    genotypes = {}
    format_str = vcf_fields[8]
    allele_position_map = get_allele_position_map(vcf_fields[3], vcf_fields[4])
    vcf_filter = vcf_fields[6].lower()

    formats = {}
    for i, item in enumerate(format_str.split(':')):
        if item == 'AD':
            formats['ad'] = i
        elif item == 'DP':
            formats['dp'] = i
        elif item == 'GQ':
            formats['gq'] = i
        elif item == 'PL':
            formats['pl'] = i

    if indivs_to_include:
        indivs_to_include = map(slugify, indivs_to_include)
    for col_index in range(9, num_columns):

        vcf_id = slugify(vcf_header_fields[col_index], separator='_')
        if vcf_id_map:
            indiv_id = vcf_id_map.get(vcf_id, vcf_id)
        else:
            indiv_id = vcf_id
        if indivs_to_include and indiv_id not in indivs_to_include:
            continue
        geno_str = vcf_fields[col_index]
        try:
            if genotype_meta:
                genotypes[indiv_id] = get_genotype_from_str(geno_str, formats, alt_allele_pos, allele_position_map, vcf_filter=vcf_filter)
            else:
                raise Exception("genotypes without meta not implemented - need to add kwarg")

        except:
            sys.stdout.write("Could not parse genotype from string: %s with format: %s. Allele_position_map: %s" % (geno_str, format_str, allele_position_map))
            raise

    variant.genotypes = genotypes

    return variant


# TODO: remove vcf_row_info
def iterate_vcf(
        vcf_file,
        genotypes=False,
        meta_fields=None,
        genotype_meta=True,
        header_info=None,
        vcf_row_info=False,
        indiv_id_list=None,
        vcf_id_map=None
):
    """
    Get the variants in a VCF file

    Args:
        vcf_file (file): VCF file, only version 4.1 is supported
        genotypes (bool): Should variants returned include genotypes? No effect if a sites VCF
        meta_fields (list): List of meta fields to parse in Variants
        genotype_meta (bool): Should genotype meta info be read? All genotype meta is None if False
        vcf_row_info(bool): Include information about the underlying VCF row in variant.meta['vcf_row_info']
        indiv_id_list(list): Only get genotypes for these individuals (helps w performance)

    Returns:
        Iterator of Variants

    """

    if indiv_id_list:
        indivs_to_include = set(indiv_id_list)
    else:
        indivs_to_include = None

    pyvcf_meta_parser = pyvcf.parser._vcf_metadata_parser()

    vcf_headers = None
    if header_info is None:
        header_info = {}

    for i, _line in enumerate(vcf_file):
        line = _line.strip('\n')
        fields = line.split('\t')

        if line.startswith('#CHROM'):
            vcf_headers = get_vcf_headers(line)

        if line.startswith('##INFO'):
            k, v = pyvcf_meta_parser.read_info(_line)
            header_info[k] = v

        if line.startswith('#'):
            continue
        
        try:
            variants = get_variants_from_vcf_fields(fields)
        except Exception, e:
            raise Exception(str(e) + " on row %s: %s" % (i, _line))
        for j, variant in enumerate(variants):

            # this is a temporary hack because mongo keys can't be big
            if len(variant.ref) + len(variant.alt) > 1000:
                continue

            # TODO: should this be in get_variants_from_vcf_fields ?
            add_vcf_info_to_variant(fields[7], variant, meta_fields=meta_fields)
            if vcf_row_info:
                d = {
                    'alt_allele_pos': j,
                    'vcf_line': _line,
                }
                variant.extras['vcf_row_info'] = d

            if genotypes:
                set_genotypes_from_vcf_fields(
                    fields,
                    variant,
                    j,
                    vcf_headers,
                    genotype_meta=genotype_meta,
                    indivs_to_include=indivs_to_include,
                    vcf_id_map=vcf_id_map
                )

                if not any([g for g in variant.genotypes.values() if g.num_alt is not None and g.num_alt > 0]):
                    # all of genotypes are hom-ref or not called
                    #print("WARNING: skipping variant: %s:%s %s %s. All genotypes are hom-ref or not called:  %s" % (variant.chr, variant.pos, variant.ref, variant.alt, 
                    continue

            yield variant


def write_sites_vcf(f, sites_list):
    """
    Write a sites VCF file to file_path
    Args:
        sites_list: iterator of (xpos, ref, alt) tuples
    Returns:
        True or False, if successful
    """
    f.write("##fileformat=VCFv4.0\n")
    f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
    for site in sites_list:
        chrom, pos = genomeloc.get_chr_pos(site[0])
        fields = [chrom[3:], str(pos), '.', site[1], site[2], '.', '.', '.']
        f.write('\t'.join(fields) + '\n')
    return True


def iterate_tuples(vcf_file):
    """
    Iterate variant tuples in a VCF file
    """
    for variant in iterate_vcf(vcf_file):
        yield variant.unique_tuple()
