import gzip
import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError
from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import GeneExpression, GeneInfo

logger = logging.getLogger(__name__)


GTEX_EXPRESSION_DATA = "http://storage.googleapis.com/gtex_analysis_v6/rna_seq_data/GTEx_Analysis_v6_RNA-seq_RNA-SeQCv1.1.8_gene_rpkm.gct.gz"
GTEX_SAMPLE_ANNOTATIONS = "http://storage.googleapis.com/gtex_analysis_v6/annotations/GTEx_Data_V6_Annotations_SampleAttributesDS.txt"


class Command(BaseCommand):
    help = "Loads GTEx tissue expression data"

    def add_arguments(self, parser):
        parser.add_argument('--gtex-expression-data', nargs="?", help="local path of '%s'" % os.path.basename(GTEX_EXPRESSION_DATA))
        parser.add_argument('--gtex-sample-annotations', nargs="?", help="local path of '%s'" % os.path.basename(GTEX_SAMPLE_ANNOTATIONS))

    def handle(self, *args, **options):
        update_gtex(
            gtex_expression_data_path = options.get("gtex_expression_data"),
            gtex_sample_annotations_path = options.get("gtex_sample_annotations"))


def update_gtex(gtex_expression_data_path=None, gtex_sample_annotations_path=None):
    if not gtex_expression_data_path:
        gtex_expression_data_path = download_file(GTEX_EXPRESSION_DATA)
    if not gtex_sample_annotations_path:
        gtex_sample_annotations_path = download_file(GTEX_SAMPLE_ANNOTATIONS)

    created_counter = total_counter = 0
    for gene_id, expression_array in get_tissue_expression_values_by_gene(
        gtex_expression_data_path,
        gtex_sample_annotations_path,
    ):
        total_counter += 1
        gene = GeneInfo.objects.filter(gene_id=gene_id).only('id').first()
        if not gene:
            logger.info("GTEx gene id not found: %s", gene_id)
            continue
        _, created = GeneExpression.objects.get_or_create(
            gene=gene,
            expression_values=expression_array)

        if created:
            created_counter += 1

    logger.info("Done. Parsed %s records from %s. Created %s new GeneExpression entries.",
        total_counter, gtex_expression_data_path, created_counter)


def get_tissue_expression_values_by_gene(expression_file_name, samples_file_name):
    """
    Return iterator of (gene_id, expression array) tuples
    Expression array is:
    expressions: {
        tissue_type: [array of expression values]
    }

    expression_file (RPKM_GeneLevel_September.gct) is in gtex format;
    samples file is just two columns: sample -> tissue type

    Command for getting samples file:
    awk -F"\t" '{ gsub(/ /,"_",$47); gsub(/-/,".",$1); print $1"\t"tolower($47) }' RNA-SeQC_metrics_September.tsv > gtex_samples.txt

    """

    # read samples file to get a map of sample_id -> tissue_type
    tissue_type_map = _get_tissue_type_map(samples_file_name)

    logger.info("Parsing %s", expression_file_name)
    with gzip.open(expression_file_name) as expression_file:
        for i, line in tqdm(enumerate(expression_file), unit=' lines'):
            line = line.rstrip('\n')
            if not line:
                break

            # first two lines are junk; third is the header
            if i < 2:
                continue
            if i == 2:
                # read header of expression file to get tissue type list
                # (used to link column to tissue type)
                # this wouldn't be necessary if samples file is in the same order as expression file,
                # but I don't wait to rely on that guarantee (mainly because they have a different # of fields)
                tissues_by_column = _get_tissues_by_column(line, tissue_type_map)
                continue

            fields = line.split('\t')
            gene_id = fields[0].split('.')[0]

            yield (gene_id, _get_expressions(line, tissues_by_column))


def _get_tissue_type_map(samples_file):
    """
    Returns map of sample id -> tissue type
    """
    logger.info("Parsing %s", samples_file)

    tissue_type_map = {}
    with open(samples_file) as f:
        header_line = f.next().rstrip('\n').split('\t')  # skip header
        assert "SMTS" in header_line, "GTEx sample file - unexpected header: %s" % header_line
        for i, line in enumerate(f):
            fields = line.rstrip('\n').split('\t')
            values = dict(zip(header_line, fields))
            sample_id = values['SAMPID']
            tissue_slug = values['SMTS'].lower().replace(" ", "_")
            tissue_detailed_slug = values['SMTSD'].lower().replace(" ", "_")
            if 'cells' in tissue_detailed_slug or 'whole_blood' in tissue_detailed_slug:
                tissue_slug = tissue_detailed_slug

            if tissue_slug not in set(GeneExpression.GTEX_TISSUE_TYPES):
                print("Skipping tissue '%s' - line #%s" % (tissue_slug, i))
                continue

            tissue_type_map[fields[0]] = tissue_slug

    return tissue_type_map


def _get_tissues_by_column(header_line, tissue_type_map):
    """
    Return a list of tissue types for each sample in header
    (len is # fields - 2, as first two fields ID the gene)
    type is None if a sample is not in tissue_type_map
    """
    header_fields = header_line.strip().split('\t')
    num_samples = len(header_fields) - 2
    tissue_types = [ None for i in range(num_samples) ]
    for i in range(num_samples):
        tissue_types[i] = tissue_type_map.get(header_fields[i+2])
    return tissue_types


def _get_expressions(line, tissues_by_column):
    """
    Make an expression map from a data line in the expression file
    """
    uniq_expressions = set(tissues_by_column)
    expressions = {e: [] for e in uniq_expressions if e is not None and e != 'na' }

    fields = line.strip().split('\t')
    for i in range(len(fields)-2):
        tissue = tissues_by_column[i]
        if expressions.has_key(tissue):
            expressions[tissue].append(float(fields[i+2]))
    return expressions
