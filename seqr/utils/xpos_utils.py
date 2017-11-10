"""
This module contains utility functions for converting (chrom, pos) pairs to/from a more compact
'xpos' representation which is a single integer that encodes both chromosome and position via
xpos = 1e9*chromosome_number + position, so for example chr1, position 12345 would be encoded as

chr1, position 12345 is xpos  1000012345
chrX, position 23552 is xpos 23000023552
"""

CHROMOSOMES = [
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7',
    '8',
    '9',
    '10',
    '11',
    '12',
    '13',
    '14',
    '15',
    '16',
    '17',
    '18',
    '19',
    '20',
    '21',
    '22',
    'X',
    'Y',
    'M',
]

CHROM_TO_CHROM_NUMBER = {chrom: i for i, chrom in enumerate(CHROMOSOMES)}
CHROM_NUMBER_TO_CHROM = {i: chrom for i, chrom in enumerate(CHROMOSOMES)}


def get_xpos(chrom, pos):
    """Compute single number representing this chromosome and position.

    Args:
        chrom (string): examples '1', 'Y', 'M'
        pos (integer): genomic position on chromosome
    """
    if chrom not in CHROM_TO_CHROM_NUMBER:
        fixed_chrom = chrom.replace('chr', '')
        if fixed_chrom.startswith('M'):
            fixed_chrom = 'M'
        if fixed_chrom not in CHROM_TO_CHROM_NUMBER:
            raise ValueError("Invalid chromosome: %s" % (chrom,))
        else:
            chrom = fixed_chrom

    if pos < 1 or pos > 3e8:
        raise ValueError("Invalid position: %s" % (pos,))

    return (1 + CHROM_TO_CHROM_NUMBER[chrom])*int(1e9) + pos


def get_chrom_pos(xpos):
    """Converts xpos position to a (chr, pos) tuple"""
    chrom_idx = int(xpos/1e9) - 1
    if chrom_idx < 0 or chrom_idx >= len(CHROMOSOMES):
        raise ValueError("Invalid xpos: %s" % (xpos,))

    return (
        CHROM_NUMBER_TO_CHROM[chrom_idx],
        xpos % int(1e9)
    )
