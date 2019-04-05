import logging
import os
from reference_data.management.commands.utils.download_utils import download_file
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneExpression

logger = logging.getLogger(__name__)

GTEX_SAMPLE_ANNOTATIONS = 'https://storage.googleapis.com/gtex_analysis_v7/annotations/GTEx_v7_Annotations_SampleAttributesDS.txt'


class GtexReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneExpression
    url = 'https://storage.googleapis.com/gtex_analysis_v7/rna_seq_data/GTEx_Analysis_2016-01-15_v7_RNASeQCv1.1.8_gene_tpm.gct.gz'
    batch_size = 1000

    def __init__(self, gtex_sample_annotations_path=None, keep_existing_records=False, **kwargs):
        if not gtex_sample_annotations_path:
            gtex_sample_annotations_path = download_file(GTEX_SAMPLE_ANNOTATIONS)
        self.tissue_type_map = _get_tissue_type_map(gtex_sample_annotations_path)
        self.tissues_by_columns = None
        self.keep_existing_records = keep_existing_records
        self.existing_gtex_gene_ids = {
            ge.gene.gene_id for ge in GeneExpression.objects.all().only('gene').prefetch_related('gene')
        } if keep_existing_records else {}

        super(GtexReferenceDataHandler, self).__init__()

    def parse_record(self, record):
        gene_id = record['Name'].split('.')[0]
        if self.keep_existing_records and gene_id in self.existing_gtex_gene_ids:
            yield None
        else:
            for tissue_type in GeneExpression.GTEX_TISSUE_TYPES:
                tissue_keys = {k for k in record.keys() if k.startswith(tissue_type)}
                expressions = []
                for tissue_key in tissue_keys:
                    tissue_type = tissue_key.split('~')[0]
                    expressions.append(float(record.pop(tissue_key)))

                if expressions:
                    yield {
                        'gene_id': gene_id,
                        'tissue_type': tissue_type,
                        'expression_values': expressions,
                    }

    def get_file_header(self, f):
        for i, line in enumerate(f):
            line = line.rstrip('\n')
            # first two lines are junk; third is the header
            if i < 2:
                continue
            if i == 2:
                # read header of expression file to get tissue type list
                # (used to link column to tissue type)
                # this wouldn't be necessary if samples file is in the same order as expression file,
                # but I don't wait to rely on that guarantee (mainly because they have a different # of fields)
                header_fields = line.strip().split('\t')
                tissue_types = ['{}~{}'.format(self.tissue_type_map.get(field), i) for i, field in enumerate(header_fields[2:])]
                return header_fields[:2] + tissue_types


class Command(GeneCommand):
    reference_data_handler = GtexReferenceDataHandler

    def add_arguments(self, parser):
        parser.add_argument('--gtex-sample-annotations-path', nargs="?", help="local path of '%s'" % os.path.basename(GTEX_SAMPLE_ANNOTATIONS))
        parser.add_argument('--keep-existing-records', help="Keep previoulsy loaded GeneExpression records", action="store_true")
        super(Command, self).add_arguments(parser)


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

            if tissue_slug in GeneExpression.GTEX_TISSUE_TYPES:
                tissue_type_map[sample_id] = tissue_slug

    logger.info("Parsed %s tissues", len(set(tissue_type_map.values())))

    return tissue_type_map
