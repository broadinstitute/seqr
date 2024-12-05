import logging
from collections import OrderedDict
from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import LATEST_GENCODE_RELEASE, OLD_GENCODE_RELEASES
from reference_data.management.commands.update_human_phenotype_ontology import update_hpo
from reference_data.management.commands.update_dbnsfp_gene import DbNSFPReferenceDataHandler
from reference_data.management.commands.update_gencode import update_gencode
from reference_data.management.commands.update_gene_constraint import GeneConstraintReferenceDataHandler
from reference_data.management.commands.update_omim import OmimReferenceDataHandler, CachedOmimReferenceDataHandler
from reference_data.management.commands.update_primate_ai import PrimateAIReferenceDataHandler
from reference_data.management.commands.update_mgi import MGIReferenceDataHandler
from reference_data.management.commands.update_gene_cn_sensitivity import CNSensitivityReferenceDataHandler
from reference_data.management.commands.update_gencc import GenCCReferenceDataHandler
from reference_data.management.commands.update_clingen import ClinGenReferenceDataHandler
from reference_data.management.commands.update_refseq import RefseqReferenceDataHandler
from reference_data.models import GeneInfo


logger = logging.getLogger(__name__)

REFERENCE_DATA_SOURCES = OrderedDict([
    ("dbnsfp_gene", DbNSFPReferenceDataHandler),
    ("gene_constraint", GeneConstraintReferenceDataHandler),
    ("gene_cn_sensitivity", CNSensitivityReferenceDataHandler),
    ("primate_ai", PrimateAIReferenceDataHandler),
    ("mgi", MGIReferenceDataHandler),
    ("gencc", GenCCReferenceDataHandler),
    ("clingen", ClinGenReferenceDataHandler),
    ("refseq", RefseqReferenceDataHandler),
    ("hpo", None),
])


class Command(BaseCommand):
    help = "Loads all reference data"

    def add_arguments(self, parser):
        omim_options = parser.add_mutually_exclusive_group(required=True)
        omim_options.add_argument('--omim-key', help="OMIM key provided with registration at http://data.omim.org/downloads")
        omim_options.add_argument('--use-cached-omim', help='Use parsed OMIM from google storage', action='store_true')
        omim_options.add_argument('--skip-omim', help="Don't reload gene constraint", action="store_true")

        parser.add_argument('--skip-gencode', help="Don't reload gencode", action="store_true")

        for source in REFERENCE_DATA_SOURCES.keys():
            parser.add_argument(
                '--skip-{}'.format(source.replace('_', '-')), help="Don't reload {}".format(source), action="store_true"
            )

    def handle(self, *args, **options):
        updated = []
        update_failed = []

        if not options["skip_gencode"]:
            if GeneInfo.objects.count() > 0:
                logger.info('Skipping update_all_reference_data because GeneInfo is already loaded')
                return
            # Download latest version first, and then add any genes from old releases not included in the latest release
            # Old gene ids are used in the gene constraint table and other datasets, as well as older sequencing data
            update_gencode(LATEST_GENCODE_RELEASE, reset=True)
            for release in OLD_GENCODE_RELEASES:
                update_gencode(release)
            updated.append('gencode')

        if not options["skip_omim"]:
            try:
                omim_handler = CachedOmimReferenceDataHandler() if options['use_cached_omim'] else \
                    OmimReferenceDataHandler(options["omim_key"])
                omim_handler.update_records()
                updated.append('omim')
            except Exception as e:
                logger.error("unable to update omim: {}".format(e))
                update_failed.append('omim')

        for source, data_handler in REFERENCE_DATA_SOURCES.items():
            if not options["skip_{}".format(source)]:
                try:
                    if data_handler:
                        data_handler().update_records()
                    elif source == "hpo":
                        update_hpo()
                    updated.append(source)
                except Exception as e:
                    logger.error("unable to update {}: {}".format(source, e))
                    update_failed.append(source)

        logger.info("Done")
        if updated:
            logger.info("Updated: {}".format(', '.join(updated)))
        if update_failed:
            logger.info("Failed to Update: {}".format(', '.join(update_failed)))
