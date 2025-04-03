import logging
from collections import OrderedDict
from django.core.management.base import BaseCommand, CommandError

from reference_data.utils.gene_utils import get_genes_by_id_and_symbol
from reference_data.models import GeneInfo, TranscriptInfo, HumanPhenotypeOntology, RefseqTranscript, GeneConstraint, \
    GeneCopyNumberSensitivity, GeneShet, Omim, dbNSFPGene, PrimateAI, MGI, GenCC, ClinGen, DataVersions
from seqr.utils.communication_utils import safe_post_to_slack
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL


logger = logging.getLogger(__name__)

REFERENCE_DATA_MODELS = [
    GeneInfo,
    Omim,
    dbNSFPGene,
    GeneConstraint,
    GeneCopyNumberSensitivity,
    PrimateAI,
    MGI,
    GenCC,
    ClinGen,
    GeneShet,
    HumanPhenotypeOntology,
]

class Command(BaseCommand):
    help = "Loads all reference data"

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration at http://data.omim.org/downloads")
        parser.add_argument('--gene-symbol-change-dir', help='Directory to upload tracked gene symbol changes')

    def handle(self, *args, **options):
        current_versions ={dv.data_model_name: dv for dv in DataVersions.objects.all()}
        latest_versions = {model: model.get_current_version(**options) for model in REFERENCE_DATA_MODELS}
        to_update = OrderedDict([
            (model, version) for model, version in latest_versions.items()
            if not current_versions.get(model.__name__) or current_versions[model.__name__].version != version
        ])
        updated = []
        update_failed = []

        if GeneInfo in to_update:
            latest_version = to_update.pop(GeneInfo)
            data_model_name = GeneInfo.__name__
            self._update_gencode(current_versions.get(data_model_name), options['gene_symbol_change_dir'])
            self._track_success_updates(data_model_name, latest_version, current_versions, updated)

        gene_ids_to_gene, gene_symbols_to_gene = get_genes_by_id_and_symbol() if to_update else (None, None)
        for data_cls, latest_version in to_update.items():
            data_model_name = data_cls.__name__
            try:
                kwargs = {'gene_ids_to_gene': gene_ids_to_gene, 'gene_symbols_to_gene': gene_symbols_to_gene}
                if data_cls == Omim and options.get('omim_key'):
                    kwargs['omim_key'] = options['omim_key']
                data_cls.update_records(**kwargs)
                self._track_success_updates(data_model_name, latest_version, current_versions, updated)
            except Exception as e:
                logger.error("unable to update {}: {}".format(data_model_name, e))
                update_failed.append(data_model_name)

        logger.info("Done")
        if updated:
            logger.info("Updated: {}".format(', '.join(updated)))
        if update_failed:
            raise CommandError("Failed to Update: {}".format(', '.join(update_failed)))

    @staticmethod
    def _track_success_updates(data_model_name, latest_version, current_versions, updated):
        current_data_version = current_versions.get(data_model_name)
        updated.append(data_model_name)
        if current_data_version:
            message = f'Updated {data_model_name} reference data from version "{current_data_version.version}" to version "{latest_version}"'
            safe_post_to_slack(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, message)
            current_data_version.version = latest_version
            current_data_version.save()
        else:
            DataVersions.objects.create(data_model_name=data_model_name, version=latest_version)

    @staticmethod
    def _update_gencode(current_data_version, gene_symbol_change_dir):
        # Download latest version first, and then add any genes from old releases not included in the latest release
        # Old gene ids are used in the gene constraint table and other datasets, as well as older sequencing data
        new_versions = GeneInfo.ALL_GENCODE_VERSIONS
        if current_data_version:
            new_versions = new_versions[:new_versions.index(current_data_version.version)]

        existing_gene_ids = set()
        existing_transcript_ids = set()
        new_transcripts = {}
        for gencode_release in new_versions:
            new_transcripts.update(GeneInfo.update_records(
                gencode_release, existing_gene_ids, existing_transcript_ids, gene_symbol_change_dir=gene_symbol_change_dir,
            ))

        if new_transcripts:
            existing_transcripts = TranscriptInfo.objects.filter(transcript_id__in=new_transcripts.keys())
            if existing_transcripts:
                deleted, _ = existing_transcripts.delete()
                logger.info(f'Dropped {deleted} existing TranscriptInfo records')

            gene_id_map, _ = get_genes_by_id_and_symbol()
            TranscriptInfo.bulk_create_for_genes(new_transcripts, gene_id_map)

        RefseqTranscript.update_records()
