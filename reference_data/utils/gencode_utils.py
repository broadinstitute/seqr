GENCODE_URL_TEMPLATE = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/{path}gencode.v{gencode_release}{file}'

# expected GTF file header
GENCODE_FILE_HEADER = [
    'chrom', 'source', 'feature_type', 'start', 'end', 'score', 'strand', 'phase', 'info'
]


def parse_gencode_record(record, new_genes, new_transcripts,  existing_gene_ids, existing_transcript_ids, counters, genome_version, gencode_release):
    if record['feature_type'] not in ('gene', 'transcript', 'CDS'):
        return

    # parse info field
    _parse_record(record)

    if len(record["chrom"]) > 2:
        return # skip super-contigs

    if record['feature_type'] == 'gene':
        if record["gene_id"] in existing_gene_ids:
            counters["genes_skipped"] += 1
            return

        new_genes[record['gene_id']].update(_parse_gene_record(record, genome_version, gencode_release))
    elif record['feature_type'] == 'transcript':
        if record["transcript_id"] in existing_transcript_ids:
            counters["transcripts_skipped"] += 1
            return

        new_transcripts[record['transcript_id']].update(_parse_transcript_record(record, genome_version))
    elif record['feature_type'] == 'CDS':
        if record["transcript_id"] in existing_transcript_ids:
            return

        coding_region_size_field_name = "coding_region_size_grch{}".format(genome_version)
        # add + 1 because GTF has 1-based coords. (https://useast.ensembl.org/info/website/upload/gff.html)
        transcript_size = record["end"] - record["start"] + 1
        transcript_size += new_transcripts[record['transcript_id']].get(coding_region_size_field_name, 0)
        new_transcripts[record['transcript_id']][coding_region_size_field_name] = transcript_size

        if record['gene_id'] not in existing_gene_ids and \
                transcript_size > new_genes[record['gene_id']].get(coding_region_size_field_name, 0):
            new_genes[record['gene_id']][coding_region_size_field_name] = transcript_size


def _parse_record(record):
    info_fields = [x.strip().split() for x in record['info'].split(';') if x != '']
    info_dict = {}
    for k, v in info_fields:
        v = v.strip('"')
        if k == 'tag':
            if k not in info_dict:
                info_dict[k] = []
            info_dict[k].append(v)
        else:
            info_dict[k] = v
    record.update(info_dict)

    record['gene_id'] = record['gene_id'].split('.')[0]
    if 'transcript_id' in record:
        record['transcript_id'] = record['transcript_id'].split('.')[0]
    record['chrom'] = record['chrom'].replace("chr", "").upper()
    record['start'] = int(record['start'])
    record['end'] = int(record['end'])


def _parse_gene_record(record, genome_version, gencode_release):
    return {
        "gene_id": record["gene_id"],
        "gene_symbol": record["gene_name"],

        "chrom_grch{}".format(genome_version): record["chrom"],
        "start_grch{}".format(genome_version): record["start"],
        "end_grch{}".format(genome_version): record["end"],
        "strand_grch{}".format(genome_version): record["strand"],

        "gencode_gene_type": record["gene_type"],
        "gencode_release": int(gencode_release),
    }


def _parse_transcript_record(record, genome_version):
    transcript = {
        "gene_id": record["gene_id"],
        "transcript_id": record["transcript_id"],
        "chrom_grch{}".format(genome_version): record["chrom"],
        "start_grch{}".format(genome_version): record["start"],
        "end_grch{}".format(genome_version): record["end"],
        "strand_grch{}".format(genome_version): record["strand"],
    }
    if 'MANE_Select' in record.get('tag', []):
        transcript['is_mane_select'] = True
    return transcript
