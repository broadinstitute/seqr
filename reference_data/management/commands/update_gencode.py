import collections
import gzip
import logging
import os
from datetime import datetime
from tqdm import tqdm

from django.db import transaction
from django.core.management.base import BaseCommand

from reference_data.models import GENOME_BUILD_GRCh37
from reference_data.models import GencodeRelease, GencodeGene, GencodeTranscript

logger = logging.getLogger(__name__)


GENCODE_FILE_PATH = "gencode.v19.annotation.gtf.gz"
RELEASE_NUMBER = 19
RELEASE_DATE = datetime(2013, 12, 1)
GENOME_BUILD_ID = GENOME_BUILD_GRCh37

class Command(BaseCommand):

    def add_arguments(self, parser):
        #parser.add_argument('gencode_file', nargs='?')
        pass

    def handle(self, *args, **options):
        #gencode_file_path = options.get('gencode_file')

        # load gencode file
        if not os.path.isfile(GENCODE_FILE_PATH):
            url = 'ftp://ftp.sanger.ac.uk/pub/gencode/Gencode_human/release_19/gencode.v19.annotation.gtf.gz'
            logger.info("Downloading %s" % url)

            #response = urllib2.urlopen(url)
            #buf = StringIO(response.read())
            #gencode_file = gzip.GzipFile(fileobj=buf)
            os.system("wget %s -O %s" % (url, GENCODE_FILE_PATH))

        gencode_file = gzip.open(GENCODE_FILE_PATH)

        # get or create GencodeRelease record
        gencode_release, created = GencodeRelease.objects.get_or_create(
            release_number=RELEASE_NUMBER, release_date=RELEASE_DATE, genome_build_id=GENOME_BUILD_ID)
        if created:
            logger.info("Created new gencode release record: %s" % gencode_release)
        else:
            logger.info("Re-loading %s" % gencode_release)

        GencodeGene.objects.all().delete()
        GencodeTranscript.objects.all().delete()

        gene_id_to_gene = {g.gene_id: g for g in GencodeGene.objects.all()}

        previously_inserted_gene_ids = set(gene_id_to_gene.keys())
        previously_inserted_transcript_ids = {t.transcript_id for t in GencodeTranscript.objects.all()}

        # parse gencode file
        counters = collections.defaultdict(int)
        for record in parse_gencode_file(gencode_file):
            counters['total_records'] += 1
            counters['%s_records' % record['feature_type']] += 1
            if record['feature_type'] == 'gene':
                if record['gene_id'] in previously_inserted_gene_ids:
                    continue

                gene_record = {
                    k: v for k, v in record.items() if k in (
                        'chrom', 'start', 'end', 'source', 'strand', 'gene_id',
                        'gene_type', 'gene_status', 'gene_name', 'level', 'protein_id'
                    )
                }

                gene_record['gencode_release'] = gencode_release

                counters['inserted_genes'] += 1
                try:
                    gene_obj = GencodeGene.objects.create(**gene_record)
                    gene_id_to_gene[record['gene_id']] = gene_obj
                except Exception as e:
                    logger.error(str(e) + " "+ str(gene_record))

            elif record['feature_type'] == 'transcript':
                if record['transcript_id'] in previously_inserted_transcript_ids:
                    continue

                transcript_record = {
                    k: v for k, v in record.items() if k in (
                        'chrom', 'start', 'end', 'source', 'strand', 'gene_id',
                        'transcript_id', 'transcript_status', 'transcript_name',
                        'transcript_support_level'
                    )
                }

                counters['inserted_transcripts'] += 1

                # NOTE: this code assumes the gencode file puts gene record before it's transcripts
                transcript_record['gencode_release'] = gencode_release
                transcript_record['gene'] = gene_id_to_gene[transcript_record['gene_id']]

                del transcript_record['gene_id']

                try:
                    GencodeTranscript.objects.create(**transcript_record)
                except Exception as e:
                    logger.error(str(e) + " "+ str(gene_record))

            elif record['feature_type'] == 'exon':
                pass # TODO save exons

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            logger.info("  %s: %s" % (k, v))


            #with transaction.atomic():
            #    GencodeGenes.objects.all().delete()

            #    GencodeGenes.objects.bulk_create(
            #        GencodeGenes(**record) for record in tqdm(records, unit=" records"),
            #    )


def parse_gencode_file(gencode_file):
    """Parses the gencode GTF file and yields a dictionary for each record

    Args:
        gencode_file: file handle
    """

    gencode_file_header = [
        'chrom', 'source', 'feature_type', 'start', 'end', 'score', 'strand', 'phase', 'info'
    ]

    for i, line in enumerate(tqdm(gencode_file, unit=' gencode records')):
        line = line.rstrip('\n')
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

        if record['feature_type'] not in ('gene', 'transcript', 'exon'):
            continue

        # parse info field
        info_fields = [x.strip().split() for x in record['info'].split(';') if x != '']
        info_fields = {k: v.strip('"') for k, v in info_fields}
        info_fields['gene_id'] = info_fields['gene_id'].split('.')[0]
        info_fields['transcript_id'] = info_fields['transcript_id'].split('.')[0]
        if 'exon_id' in info_fields:
            info_fields['exon_id'] = info_fields['exon_id'].split('.')[0]

        # add info field keys, values to record
        record.update(info_fields)

        # modify some of the fields
        record['chrom'] = record['chrom'][3:4].upper()
        record['start'] = int(record['start'])
        record['end'] = int(record['end'])
        record['source'] = record['source'][0].upper()
        record['gene_status'] = record['gene_status'][0].upper()
        record['transcript_status'] = record['transcript_status'][0].upper()

        del record['info']

        yield record

