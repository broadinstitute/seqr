import collections
import gzip
import logging
from tqdm import tqdm

from django.core.management.base import BaseCommand

from reference_data.management.commands.file_utils import download_remote_file
from reference_data.models import GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38
from reference_data.models import GencodeGene, GencodeTranscript

logger = logging.getLogger(__name__)


# from https://www.gencodegenes.org/releases/current.html
GENCODE_GTF_FILES = {
    GENOME_VERSION_GRCh38: "ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_28/gencode.v28.annotation.gtf.gz",
    GENOME_VERSION_GRCh37: "ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_28/GRCh37_mapping/gencode.v28lift37.annotation.gtf.gz",
}


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        for genome_version, gencode_gtf_url in GENCODE_GTF_FILES.items():
            counters = collections.defaultdict(int)

            local_file_path = download_remote_file(gencode_gtf_url)
            logger.info("Parsing " + local_file_path)
            gene_dicts = []
            transcript_dicts = []
            for gencode_record_dict in parse_gencode_file(gzip.open(local_file_path)):
                counters['total_records'] += 1
                counters['%s_records' % gencode_record_dict['feature_type']] += 1

                gencode_record_dict['genome_version'] = genome_version
                if gencode_record_dict['feature_type'] == 'gene':
                    gene_dicts.append({
                        k: v for k, v in gencode_record_dict.items() if k in GencodeGene._meta.json_fields
                    })

                elif gencode_record_dict['feature_type'] == 'transcript':
                    transcript_dicts.append({
                        k: v for k, v in gencode_record_dict.items() if k in GencodeTranscript._meta.json_fields
                    })

                elif gencode_record_dict['feature_type'] == 'exon':
                    pass  # TODO save exons?

            gene_records = []
            gene_id_to_gene = {}
            for gene_dict in tqdm(gene_dicts, unit=" gene records"):
                try:
                    gene_record = GencodeGene(**gene_dict)
                except Exception as e:
                    logger.error(str(e) + " " + str(gene_dict))
                else:
                    gene_id_to_gene[gene_dict['gene_id']] = gene_record
                    gene_records.append(gene_record)


            logger.info("Creating {} gene records..".format(len(gene_records)))
            GencodeGene.objects.filter(genome_version=genome_version).delete()
            GencodeGene.objects.bulk_create((gr for gr in tqdm(gene_records)))

            transcript_records = []
            for transcript_dict in tqdm(transcript_dicts, unit=" transcript records"):
                transcript_dict['gene'] = gene_id_to_gene[transcript_dict['gene_id']]
                del transcript_dict['gene_id']

                try:
                    transcript_record = GencodeTranscript(**transcript_dict)
                except Exception as e:
                    logger.error(str(e) + " " + str(transcript_record))
                else:
                    transcript_records.append(transcript_record)

            logger.info("Creating {} transcript records..".format(len(transcript_records)))
            GencodeTranscript.objects.filter(genome_version=genome_version).delete()
            GencodeTranscript.objects.bulk_create(transcript_records)

            logger.info("Done")

            logger.info("Stats: ")
            for k, v in counters.items():
                logger.info("  %s: %s" % (k, v))


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

        if record['feature_type'] not in ('gene', 'transcript'): #, 'exon'):
            continue

        def remove_version_suffix(feature_id):
            return feature_id.split('.')[0]   # converts id like "ENST00012345.3" to "ENST00012345"

        try:
            # parse info field
            info_fields = [x.strip().split() for x in record['info'].split(';') if x != '']
            info_fields = {k: v.strip('"') for k, v in info_fields}
            info_fields['gene_id'] = remove_version_suffix(info_fields['gene_id'])
            if 'transcript_id' in info_fields:
                info_fields['transcript_id'] = remove_version_suffix(info_fields['transcript_id'])
            if 'exon_id' in info_fields:
                info_fields['exon_id'] = remove_version_suffix(info_fields['exon_id'])

            # add info field keys, values to record
            record.update(info_fields)

            # modify some of the fields
            record['chrom'] = record['chrom'][3:4].upper()
            record['start'] = int(record['start'])
            record['end'] = int(record['end'])
            record['source'] = record['source'][0].upper()
        except Exception as e:
            logger.info("Error: {} when parsing record {}: ".format(str(e), record))
            continue

        del record['info']

        yield record

