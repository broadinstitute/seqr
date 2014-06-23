from xbrowse.core.genomeloc import get_xpos

def get_data_from_gencode_gtf(gtf_file):
    """
    Parse gencode GTF file
    Returns iter of (datatype, dict) tuples
    datatype is one of gene, transcript, exon
    dict is the corresponding object
    """
    for line in gtf_file:
        if line.startswith('#'):
            continue
        fields = line.strip('\n').split('\t')

        # only look at ensembl genes. may want to change this
        if fields[1] != 'ENSEMBL' and fields[2] not in ['gene', 'transcript', 'exon']:
            continue

        chrom = fields[0][3:]
        start = int(fields[3]) + 1  # bed files are 0-indexed
        stop = int(fields[4]) + 1
        info = dict(x.strip().split() for x in fields[8].split(';') if x != '')
        info = {k: v.strip('"') for k, v in info.items()}
        if 'gene_id' in info:
            info['gene_id'] = info['gene_id'].split('.')[0]
        if 'transcript_id' in info:
            info['transcript_id'] = info['transcript_id'].split('.')[0]
        if 'exon_id' in info:
            info['exon_id'] = info['exon_id'].split('.')[0]

        info['chrom'] = chrom
        info['start'] = start
        info['stop'] = stop
        info['xstart'] = get_xpos(chrom, start),
        info['xstop'] = get_xpos(chrom, stop),

        yield fields[2], info
