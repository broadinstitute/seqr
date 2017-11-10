from xbrowse.core.genomeloc import get_xpos

def get_data_from_gencode_gtf(gtf_file):
    """
    Parse gencode GTF file
    Returns iter of (datatype, dict) tuples
    datatype is one of gene, transcript, exon, cds
    dict is the corresponding object
    """
    for line in gtf_file:
        if line.startswith('#'):
            continue
        fields = line.strip('\n').split('\t')

        if fields[2] not in ['gene', 'transcript', 'exon', 'CDS']:
            continue

        chrom = fields[0][3:]
        if len(chrom) > 3:
            continue # skip the pseudo contigs

        start = int(fields[3])  # GTF files are 1-indexed: http://www.ensembl.org/info/website/upload/gff.html
        stop = int(fields[4])
        info = dict(x.strip().split() for x in fields[8].split(';') if x != '')
        info = {k: v.strip('"') for k, v in info.items()}
        if 'gene_id' in info:
            info['gene_id'] = info['gene_id'].split('.')[0]

            # TODO: ignore all entities that are part of an ENSGR gene
            if info['gene_id'].startswith('ENSGR'):
                continue

        if 'transcript_id' in info:
            info['transcript_id'] = info['transcript_id'].split('.')[0]
        if 'exon_id' in info:
            info['exon_id'] = info['exon_id'].split('.')[0]

        info['chrom'] = chrom
        info['start'] = start
        info['stop'] = stop
        info['xstart'] = get_xpos(chrom, start)
        info['xstop'] = get_xpos(chrom, stop)

        # pretend 'CDS' isn't capitalized in gencode gtf file
        yield fields[2].lower(), info
