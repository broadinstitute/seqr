def get_chr_from_seq_region_name(seq_region_name):
    """
    In the REST API, {"seq_region_name": "7"} is what we'd call "chr7"
    """
    if seq_region_name == 'X':
        return 'chrX'
    elif seq_region_name == 'Y':
        return 'chrY'
    try:
        chr_int = int(seq_region_name)
    except ValueError:
        return None
    if chr_int < 1 or chr_int > 22:
        return None
    return 'chr%d' % chr_int