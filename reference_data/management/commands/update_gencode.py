import collections
import gzip
import logging
import os
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DataError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)

GENCODE_GTF_URL = "ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.annotation.gtf.gz"
GENCODE_LIFT37_GTF_URL = "ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/GRCh37_mapping/gencode.v{gencode_release}lift37.annotation.gtf.gz"


class Command(BaseCommand):
    help = "Loads the GRCh37 and/or GRCh38 versions of the Gencode GTF from a particular Gencode release"

    def add_arguments(self, parser):
        parser.add_argument('--reset', help="First drop any existing records from GeneInfo and TranscriptInfo", action="store_true")
        parser.add_argument('--gencode-release', help="gencode release number (eg. 28)", type=int, required=True, choices=range(19, 29))
        parser.add_argument('gencode_gtf_path', nargs="?", help="(optional) gencode GTF file path. If not specified, it will be downloaded.")
        parser.add_argument('genome_version', nargs="?", help="gencode GTF file genome version", choices=[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38])

    def handle(self, *args, **options):

        update_gencode(
            gencode_release=options['gencode_release'],
            gencode_file_path=options.get('gencode_gtf_path'),
            genome_version=options.get('genome_version'),
            reset=options['reset'])


def update_gencode(gencode_release, gencode_file_path=None, genome_version=None, reset=False):
    """Update GeneInfo and TranscriptInfo tables.

    Args:
        gencode_release (int): the gencode release to load (eg. 25)
        gencode_file_path (str): optional local file path of gencode GTF file. If not provided, it will be downloaded.
        genome_version (str): '37' or '38'. Required only if gencode_file_path is specified.
        reset (bool): If True, all records will be deleted from GeneInfo and TranscriptInfo before loading the new data.
            Setting this to False can be useful to sequentially load more than one gencode release so that data in the
            tables represents the union of multiple gencode releases.
    """
    if gencode_file_path and genome_version and os.path.isfile(gencode_file_path):
        if gencode_release == 19 and genome_version != GENOME_VERSION_GRCh37:
            raise CommandError("Invalid genome_version: {}. gencode v19 only has a GRCh37 version".format(genome_version))
        elif gencode_release <= 22 and genome_version != GENOME_VERSION_GRCh38:
            raise CommandError("Invalid genome_version: {}. gencode v20, v21, v22 only have a GRCh38 version".format(genome_version))
        elif (genome_version == GENOME_VERSION_GRCh38) ^ ("lift" in gencode_file_path.lower()):
            raise CommandError("Invalid genome_version for file: {}. gencode v23 and up must have 'lift' in the filename or genome_version arg must be GRCh38".format(gencode_file_path))

        gencode_file_paths = {genome_version: gencode_file_path}
    elif gencode_file_path and not genome_version:
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
        gencode_file_paths = {}
        for genome_version, url in urls:
            local_filename = download_file(url)
            gencode_file_paths.update({genome_version: local_filename})

    if reset:
        logger.info("Dropping the {} existing TranscriptInfo entries".format(TranscriptInfo.objects.count()))
        TranscriptInfo.objects.all().delete()
        logger.info("Dropping the {} existing GeneInfo entries".format(GeneInfo.objects.count()))
        GeneInfo.objects.all().delete()

    for genome_version, gencode_file_path in gencode_file_paths.items():
        load_gencode_gtf_file(gencode_file_path, genome_version, gencode_release)


def load_gencode_gtf_file(gencode_file_path, genome_version, gencode_release):
    """Parses and loads the given gencode GTF file into the GeneInfo and TranscriptInfo tables.

    Args:
        gencode_file_path (str): local file path
        genome_version (str): "37" or "38"
        gencode_release (int):  gencode release verison (eg. 25)
    """

    gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.all().only('gene_id')}
    transcript_id_to_transcript_info = {t.transcript_id: t for t in TranscriptInfo.objects.all().only('transcript_id')}

    logger.info("Loading {}  (genome version: {})".format(gencode_file_path, genome_version))
    with gzip.open(gencode_file_path) as gencode_file:

        counters = collections.defaultdict(int)
        transcript_id_to_cds_size = collections.defaultdict(int)
        for i, record in enumerate(_parse_gencode_file(gencode_file)):
            if len(record["chrom"]) > 2:
                continue  # skip super-contigs

            if record['feature_type'] == 'gene':
                record = {
                    "gene_id": record["gene_id"],
                    "gene_symbol": record["gene_name"],

                    "chrom_grch{}".format(genome_version): record["chrom"],
                    "start_grch{}".format(genome_version): record["start"],
                    "end_grch{}".format(genome_version): record["end"],
                    "strand_grch{}".format(genome_version): record["strand"],

                    "gencode_gene_type": record["gene_type"],
                    "gencode_release": int(gencode_release),
                }

                gene_info = gene_id_to_gene_info.get(record['gene_id'])

                try:
                    if gene_info:
                        counters["genes_updated"] += 1
                        for key, value in record.items():
                            setattr(gene_info, key, value)
                        gene_info.save()
                    else:
                        counters["genes_created"] += 1
                        gene_info = GeneInfo.objects.create(**record)
                except DataError as e:
                    logger.error("ERROR: {} on record #{}: {} ".format(e, i, record))

                gene_id_to_gene_info[record['gene_id']] = gene_info

            elif record['feature_type'] == 'transcript':
                record = {
                    "gene": gene_id_to_gene_info[record['gene_id']],  # assumes that gene records are before transcript records in the GTF
                    "transcript_id": record["transcript_id"],
                    "chrom_grch{}".format(genome_version): record["chrom"],
                    "start_grch{}".format(genome_version): record["start"],
                    "end_grch{}".format(genome_version): record["end"],
                    "strand_grch{}".format(genome_version): record["strand"],
                }

                transcript_info = transcript_id_to_transcript_info.get(record['transcript_id'])
                try:
                    if transcript_info:
                        counters["transcripts_updated"] += 1
                        for key, value in record.items():
                            setattr(transcript_info, key, value)
                        transcript_info.save()
                    else:
                        counters["transcripts_created"] += 1
                        transcript_info = TranscriptInfo.objects.create(**record)
                except DataError as e:
                    logger.error("ERROR: {} on record #{}: {} ".format(e, i, record))
                transcript_id_to_transcript_info[record['transcript_id']] = transcript_info

            elif record['feature_type'] == 'CDS':
                # add + 1 because GTF has 1-based coords. (https://useast.ensembl.org/info/website/upload/gff.html)
                transcript_id_to_cds_size[record["transcript_id"]] += int(record["end"]) - int(record["start"]) + 1

    _update_coding_region_sizes(transcript_id_to_transcript_info, transcript_id_to_cds_size, genome_version)

    logger.info("Done")
    logger.info("Stats: ")
    for k, v in counters.items():
        logger.info("  %s: %s" % (k, v))


def _update_coding_region_sizes(transcript_id_to_transcript_info, transcript_id_to_cds_size, genome_version):
    """Sets the gencode_coding_region_size_grch{genome_version} field for

    Args:
        transcript_id_to_transcript_info (dict): maps ENST transcript ID to its TranscriptInfo object.
        transcript_id_to_cds_size (dict): for coding transcripts, maps ENST transcript IDs to their coding region size.
        genome_version (str): "37" or "38"
    """
    coding_region_size_field_name = "coding_region_size_grch{}".format(genome_version)

    logger.info("Updating {}".format(coding_region_size_field_name))
    for transcript_id, coding_region_size in tqdm(transcript_id_to_cds_size.items(), unit=" transcripts"):
        transcript_info = transcript_id_to_transcript_info[transcript_id]
        setattr(transcript_info, coding_region_size_field_name, coding_region_size)
        transcript_info.save()

        gene_info = transcript_info.gene
        if coding_region_size > getattr(gene_info, coding_region_size_field_name):
            setattr(gene_info, coding_region_size_field_name, coding_region_size)
            gene_info.save()


def _parse_gencode_file(gencode_file):
    """Parses the gencode GTF file and yields a simple dictionary for each record

    Args:
        gencode_file: file handle
    """

    # expected GTF file header
    gencode_file_header = [
        'chrom', 'source', 'feature_type', 'start', 'end', 'score', 'strand', 'phase', 'info'
    ]

    for i, line in enumerate(tqdm(gencode_file, unit=' gencode records')):
        line = line.rstrip('\r\n')
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')

        if len(fields) != len(gencode_file_header):
            raise ValueError("Unexpected number of fields on line #%s: %s" % (i, fields))

        record = dict(zip(gencode_file_header, fields))

        # Feature types in gencode v19:
        #   1196293 exon
        #    723784 CDS
        #    284573 UTR
        #    196520 transcript
        #     84144 start_codon
        #     76196 stop_codon
        #     57820 gene
        #       114 Selenocysteine

        if record['feature_type'] not in ('gene', 'transcript', 'exon', 'CDS'):
            continue

        # parse info field
        info_fields = [x.strip().split() for x in record['info'].split(';') if x != '']
        info_fields = {k: v.strip('"') for k, v in info_fields}
        info_fields['gene_id'] = info_fields['gene_id'].split('.')[0]
        if 'transcript_id' in info_fields:
            info_fields['transcript_id'] = info_fields['transcript_id'].split('.')[0]
        if 'exon_id' in info_fields:
            info_fields['exon_id'] = info_fields['exon_id'].split('.')[0]

        # add info field keys, values to record
        record.update(info_fields)

        # modify some of the fields
        record['chrom'] = record['chrom'].replace("chr", "").upper()
        record['start'] = int(record['start'])
        record['end'] = int(record['end'])
        record['source'] = record['source'][0].upper()
        del record['info']

        yield record

