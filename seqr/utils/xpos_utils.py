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

CHROM_TO_CHROM_NUMBER = {chrom : i+1 for i, chrom in enumerate(CHROMOSOMES)}
CHROM_NUMBER_TO_CHROM = {i+1: chrom for i, chrom in enumerate(CHROMOSOMES)}


def get_xpos(chrom, pos):
    """Compute single number representing this chromosome and position.

    Args:
        chrom (string): examples '1', 'Y', 'M'
        pos (integer): genomic position on chromosome
    """
    return (CHROM_TO_CHROM_NUMBER[chrom]+1) * int(1e9) + pos


def get_chrom_pos(xpos):
    """
    Gets a (chr, pos) tuple from a single location
    """
    return CHROM_NUMBER_TO_CHROM[int(xpos/1e9)], xpos % int(1e9)
