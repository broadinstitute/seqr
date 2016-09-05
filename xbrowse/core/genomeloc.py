"""
TODO: let's name this xpos.py
"""

import re

CHR_REGEX = re.compile(r'^(chr[\d|X|Y|M]+)$')

CHR_POS_REGEX = re.compile(r'^(chr[\d|X|Y|M]+):(\d+)$')
NOCHR_POS_REGEX = re.compile(r'^([\d|X|Y|M]+):(\d+)$')
CHR_WHITESPACE_REGEX = re.compile(r'^(chr[\d|X|Y|M]+)\s+(\d+)$')
NOCHR_WHITESPACE_REGEX = re.compile(r'^([\d|X|Y|M]+)\s+(\d+)$')

CHR_POS_REGION_REGEX = re.compile(r'^(chr[\d|X|Y|M]+):(\d+)[\-|\.]+(\d+)$')
NOCHR_POS_REGION_REGEX = re.compile(r'^([\d|X|Y|M]+):(\d+)[\-|..](\d+)$')
CHR_WHITESPACE_REGION_REGEX = re.compile(r'^(chr[\d|X|Y|M]+)\s+(\d+)\s+(\d+)$')
NOCHR_WHITESPACE_REGION_REGEX = re.compile(r'^([\d|X|Y|M]+)\s+(\d+)\s+(\d+)$')

CHROMOSOMES = [
    'chr1',
    'chr2',
    'chr3',
    'chr4',
    'chr5',
    'chr6',
    'chr7',
    'chr8',
    'chr9',
    'chr10',
    'chr11',
    'chr12',
    'chr13',
    'chr14',
    'chr15',
    'chr16',
    'chr17',
    'chr18',
    'chr19',
    'chr20',
    'chr21',
    'chr22',
    'chrX',
    'chrY',
    'chrM',
]

CHROMOSOME_TO_CODE = {}
CHROMOSOME_TO_CODE.update({ chrom: i+1 for i, chrom in enumerate(CHROMOSOMES) })
CHROMOSOME_TO_CODE.update({ chrom.replace('chr', ''): i+1 for i, chrom in enumerate(CHROMOSOMES) })
CODE_TO_CHROMOSOME = { code: chr for chr, code in CHROMOSOME_TO_CODE.items() }

def valid_pos(chr, bp): 
    """
    True/False if it is a valid position - chr name is known and bp isn't out of bounds
    bounds are between 1 and 3e8...implication is 0-indexed
    TODO: Note that pos could be greater than chromosome length for smaller chromosomes, fix that
    """
    if not isinstance(chr, basestring):
        raise ValueError('chr must be a string')
    if not CHROMOSOME_TO_CODE.has_key(chr) and not CHROMOSOME_TO_CODE.has_key('chr' + chr):
        return False
    if bp < 1 or bp > 3e8:
        return False
    return True

def get_single_location(chr, pos): 
    """
    Gets a single location from chromosome and position
    chr must be actual chromosme code (chrY) and pos must be integer
    """
    return CHROMOSOME_TO_CODE[chr] * int(1e9) + pos

def get_chr_pos(single_location): 
    """
    Gets a (chr, pos) tuple from a single location
    """
    return CODE_TO_CHROMOSOME[int(single_location/1e9)], single_location%int(1e9)

def get_range(chr, bp1, ref, alt): 
    """
    Get (start, end) tuple in single location format
    """
    start = get_single_location(chr, bp1)
    if len(ref) == len(alt):
        end = start
    elif len(ref) > len(alt):
        end = start + len(ref) - len(alt)
    else:
        end = start - 1
    return (start, end)

def get_single_location_from_string(random_string): 
    """
    Get single location from user input string
    Should be in formats:
    -- chr1
    -- chr1:10
    -- 1:10
    -- chr1 10 (separated by any whitespace)
    -- 1 10 (separated by any whitespace)
    """
    m = CHR_POS_REGEX.match(random_string)
    if m:
        return get_single_location(m.group(1), int(m.group(2)))

    m = NOCHR_POS_REGEX.match(random_string)
    if m:
        return get_single_location('chr' + m.group(1), int(m.group(2)))

    m = CHR_WHITESPACE_REGEX.match(random_string)
    if m:
        return get_single_location(m.group(1), int(m.group(2)))

    m = NOCHR_WHITESPACE_REGEX.match(random_string)
    if m:
        return get_single_location('chr' + m.group(1), int(m.group(2)))

    return None

def get_range_single_location_from_string(random_string): 
    """
    Get a range from user input string
    Should be in formats:
    -- chr1:1-10
    -- 1:1-10
    -- 1 1 10 (start of a BED file, can be separated by any whitespace)
    -- rs1:rs2 (not implemented yet though, as we don't have dbSNP attached)
    Returns a (start, end) tuple
    """
    m = CHR_REGEX.match(random_string)
    if m:
        start = get_single_location(m.group(1), 0)
        end = start + int(5e8)
        return (start, end)

    m = CHR_POS_REGION_REGEX.match(random_string)
    if m:
        start = get_single_location(m.group(1), int(m.group(2)))
        end = get_single_location(m.group(1), int(m.group(3)))
        return (start, end)

    m = NOCHR_POS_REGION_REGEX.match(random_string)
    if m:
        start = get_single_location('chr' + m.group(1), int(m.group(2)))
        end = get_single_location('chr' + m.group(1), int(m.group(3)))
        return (start, end)

    m = CHR_WHITESPACE_REGION_REGEX.match(random_string)
    if m:
        start = get_single_location(m.group(1), int(m.group(2)))
        end = get_single_location(m.group(1), int(m.group(3)))
        return (start, end)

    m = NOCHR_WHITESPACE_REGION_REGEX.match(random_string)
    if m:
        start = get_single_location('chr' + m.group(1), int(m.group(2)))
        end = get_single_location('chr' + m.group(1), int(m.group(3)))
        return (start, end)

    return None


def get_xpos(chrom, pos):
    """
    This is now the preferred getter
    """
    if not chrom.startswith('chr'):
        chrom = 'chr{}'.format(chrom)
    return get_single_location(chrom, pos)
