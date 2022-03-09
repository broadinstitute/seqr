import collections
import gzip
import logging
import os
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)

GENCODE_GTF_URL = "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.annotation.gtf.gz"
GENCODE_LIFT37_GTF_URL = "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/GRCh37_mapping/gencode.v{gencode_release}lift37.annotation.gtf.gz"

# expected GTF file header
GENCODE_FILE_HEADER = [
    'chrom', 'source', 'feature_type', 'start', 'end', 'score', 'strand', 'phase', 'info'
]


class Command(BaseCommand):
    help = "Loads the GRCh37 and/or GRCh38 versions of the Gencode GTF from a particular Gencode release"

    def add_arguments(self, parser):
        parser.add_argument('--reset', help="First drop any existing records from GeneInfo and TranscriptInfo", action="store_true")
        parser.add_argument('--gencode-release', help="gencode release number (eg. 28)", type=int, required=True, choices=range(19, 32))
        parser.add_argument('gencode_gtf_path', nargs="?", help="(optional) gencode GTF file path. If not specified, it will be downloaded.")
        parser.add_argument('genome_version', nargs="?", help="gencode GTF file genome version", choices=[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38])

    def handle(self, *args, **options):

        update_gencode(
            gencode_release=options['gencode_release'],
            gencode_gtf_path=options.get('gencode_gtf_path'),
            genome_version=options.get('genome_version'),
            reset=options['reset'])


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


def update_gencode(gencode_release, gencode_gtf_path=None, genome_version=None, reset=False):
    """Update GeneInfo and TranscriptInfo tables.

    Args:
        gencode_release (int): the gencode release to load (eg. 25)
        gencode_gtf_path (str): optional local file path of gencode GTF file. If not provided, it will be downloaded.
        genome_version (str): '37' or '38'. Required only if gencode_gtf_path is specified.
        reset (bool): If True, all records will be deleted from GeneInfo and TranscriptInfo before loading the new data.
            Setting this to False can be useful to sequentially load more than one gencode release so that data in the
            tables represents the union of multiple gencode releases.
    """
    gencode_gtf_paths = _get_valid_gencode_gtf_paths(gencode_release, gencode_gtf_path, genome_version)

    if reset:
        logger.info("Dropping the {} existing TranscriptInfo entries".format(TranscriptInfo.objects.count()))
        TranscriptInfo.objects.all().delete()
        logger.info("Dropping the {} existing GeneInfo entries".format(GeneInfo.objects.count()))
        GeneInfo.objects.all().delete()

    existing_gene_ids = {gene.gene_id for gene in GeneInfo.objects.all().only('gene_id')}
    existing_transcript_ids = {
        transcript.transcript_id for transcript in TranscriptInfo.objects.all().only('transcript_id')
    }

    counters = collections.defaultdict(int)
    new_genes = collections.defaultdict(dict)
    new_transcripts = collections.defaultdict(dict)

    for genome_version, gencode_gtf_path in gencode_gtf_paths.items():
        logger.info("Loading {} (genome version: {})".format(gencode_gtf_path, genome_version))
        with gzip.open(gencode_gtf_path, 'rt') as gencode_file:
            for i, line in enumerate(tqdm(gencode_file, unit=' gencode records')):
                _parse_line(
                    line, i, new_genes, new_transcripts, existing_gene_ids, existing_transcript_ids, counters,
                    genome_version, gencode_release)

    logger.info('Creating {} GeneInfo records'.format(len(new_genes)))
    counters["genes_created"] = len(new_genes)
    GeneInfo.objects.bulk_create([GeneInfo(**record) for record in new_genes.values()])
    gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.all().only('gene_id')}

    logger.info('Creating {} TranscriptInfo records'.format(len(new_transcripts)))
    counters["transcripts_created"] = len(new_transcripts)
    TranscriptInfo.objects.bulk_create([
        TranscriptInfo(gene=gene_id_to_gene_info[record.pop('gene_id')], **record) for record in new_transcripts.values()
    ], batch_size=50000)

    logger.info("Done")
    logger.info("Stats: ")
    for k, v in counters.items():
        logger.info("  %s: %s" % (k, v))

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
    info_fields = {k: v.strip('"') for k, v in info_fields}
    record.update(info_fields)

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