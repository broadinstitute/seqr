import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneConstraint

logger = logging.getLogger(__name__)


class GeneConstraintReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneConstraint
    url = "http://storage.googleapis.com/seqr-reference-data/gene_constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt"

    @staticmethod
    def parse_record(record):
        yield {
            'gene_id': record['gene_id'].split(".")[0],
            'gene_symbol': record['gene'],
            'mis_z': float(record['mis_z']) if record['mis_z'] != 'NaN' else -100,
            'pLI': float(record['pLI']) if record['pLI'] != 'NA' else 0,
            'louef': float(record['oe_lof']) if record['oe_lof'] != 'NA' else 100,
        }

    @staticmethod
    def post_process_models(models):
        # add _rank fields
        for field, order in [('mis_z', -1), ('pLI', -1), ('louef', 1)]:
            for i, model in enumerate(sorted(models, key=lambda model: order * getattr(model, field))):
                setattr(model, '{}_rank'.format(field), i)


class Command(GeneCommand):
    reference_data_handler = GeneConstraintReferenceDataHandler
