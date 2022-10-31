import collections
import gzip
import logging
import os
from tqdm import tqdm

from django.core.management.base import CommandError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)

LATEST_GENCODE_RELEASE = 31
OLD_GENCODE_RELEASES = [29, 28, 27, 19]

GENCODE_GTF_URL = "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.annotation.gtf.gz"
GENCODE_LIFT37_GTF_URL = "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/GRCh37_mapping/gencode.v{gencode_release}lift37.annotation.gtf.gz"

# expected GTF file header
GENCODE_FILE_HEADER = [
    'chrom', 'source', 'feature_type', 'start', 'end', 'score', 'strand', 'phase', 'info'
]


def _get_valid_gencode_gtf_paths(gencode_release, gencode_gtf_path, genome_version):
    if gencode_gtf_path and genome_version and os.path.isfile(gencode_gtf_path):
        if gencode_release == 19 and genome_version != GENOME_VERSION_GRCh37:
            raise CommandError("Invalid genome_version: {}. gencode v19 only has a GRCh37 version".format(genome_version))
        elif gencode_release <= 22 and genome_version != GENOME_VERSION_GRCh38:
            raise CommandError("Invalid genome_version: {}. gencode v20, v21, v22 only have a GRCh38 version".format(genome_version))
        elif genome_version != GENOME_VERSION_GRCh38 and "lift" not in gencode_gtf_path.lower():
            raise CommandError("Invalid genome_version for file: {}. gencode v23 and up must have 'lift' in the filename or genome_version arg must be GRCh38".format(gencode_gtf_path))

        gencode_gtf_paths = {genome_version: gencode_gtf_path}
    elif gencode_gtf_path and not genome_version:
        raise CommandError("The genome version must also be specified after the gencode GTF file path")
    else:
        if gencode_release == 19:
            urls = [('37', GENCODE_GTF_URL.format(gencode_release=gencode_release))]
        elif gencode_release <= 22:
            urls = [('38', GENCODE_GTF_URL.format(gencode_release=gencode_release))]
        else:
            urls = [
                ('37', GENCODE_LIFT37_GTF_URL.format(gencode_release=gencode_release)),
                ('38', GENCODE_GTF_URL.format(gencode_release=gencode_release)),
            ]
        gencode_gtf_paths = {}
        for genome_version, url in urls:
            local_filename = download_file(url)
            gencode_gtf_paths.update({genome_version: local_filename})
    return gencode_gtf_paths


def load_gencode_records(gencode_release, gencode_gtf_path=None, genome_version=None, existing_gene_ids=None, existing_transcript_ids=None):
    gencode_gtf_paths = _get_valid_gencode_gtf_paths(gencode_release, gencode_gtf_path, genome_version)

    counters = collections.defaultdict(int)
    new_genes = collections.defaultdict(dict)
    new_transcripts = collections.defaultdict(dict)

    for genome_version, gencode_gtf_path in gencode_gtf_paths.items():
        logger.info("Loading {} (genome version: {})".format(gencode_gtf_path, genome_version))
        with gzip.open(gencode_gtf_path, 'rt') as gencode_file:
            for i, line in enumerate(tqdm(gencode_file, unit=' gencode records')):
                _parse_line(
                    line, i, new_genes, new_transcripts, existing_gene_ids or set(), existing_transcript_ids or set(),
                    counters, genome_version, gencode_release)

    return new_genes, new_transcripts, counters


def create_transcript_info(new_transcripts):
    gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.order_by('gencode_release').only('gene_id')}
    logger.info('Creating {} TranscriptInfo records'.format(len(new_transcripts)))
    TranscriptInfo.objects.bulk_create([
        TranscriptInfo(gene=gene_id_to_gene_info[record.pop('gene_id')], **record) for record in
        new_transcripts.values()
    ], batch_size=50000)


def _parse_line(line, i, new_genes, new_transcripts,  existing_gene_ids, existing_transcript_ids, counters, genome_version, gencode_release):
    line = line.rstrip('\r\n')
    if not line or line.startswith('#'):
        return
    fields = line.split('\t')

    if len(fields) != len(GENCODE_FILE_HEADER):
        raise ValueError("Unexpected number of fields on line #%s: %s" % (i, fields))

    record = dict(zip(GENCODE_FILE_HEADER, fields))

    if record['feature_type'] not in ('gene', 'transcript', 'CDS'):
        return

    # parse info field
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

    if len(record["chrom"]) > 2:
        return  # skip super-contigs

    if record['feature_type'] == 'gene':
        if record["gene_id"] in existing_gene_ids:
            counters["genes_skipped"] += 1
            return

        new_genes[record['gene_id']].update({
            "gene_id": record["gene_id"],
            "gene_symbol": record["gene_name"],

            "chrom_grch{}".format(genome_version): record["chrom"],
            "start_grch{}".format(genome_version): record["start"],
            "end_grch{}".format(genome_version): record["end"],
            "strand_grch{}".format(genome_version): record["strand"],

            "gencode_gene_type": record["gene_type"],
            "gencode_release": int(gencode_release),
        })

    elif record['feature_type'] == 'transcript':
        if record["transcript_id"] in existing_transcript_ids:
            counters["transcripts_skipped"] += 1
            return

        new_transcripts[record['transcript_id']].update({
            "gene_id": record["gene_id"],
            "transcript_id": record["transcript_id"],
            "chrom_grch{}".format(genome_version): record["chrom"],
            "start_grch{}".format(genome_version): record["start"],
            "end_grch{}".format(genome_version): record["end"],
            "strand_grch{}".format(genome_version): record["strand"],
        })
        if 'MANE_Select' in record.get('tag', []):
            new_transcripts[record['transcript_id']]['is_mane_select'] = True

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