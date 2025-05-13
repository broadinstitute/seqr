from reference_data.models import GENOME_VERSION_GRCh38

def vlm_lookup(user, chrom, pos, ref, alt, genome_version=None, **kwargs):
    genome_version = genome_version or GENOME_VERSION_GRCh38
    return {'chrom': chrom, 'pos': pos, 'ref': ref, 'alt': alt, 'genome_version': genome_version}