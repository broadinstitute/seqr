import logging
from django.core.management.base import BaseCommand, CommandError

from reference_data.utils.gene_utils import get_genes_by_id_and_symbol
from reference_data.models import GeneInfo, TranscriptInfo, HumanPhenotypeOntology, RefseqTranscript, GeneConstraint, \
    GeneCopyNumberSensitivity, GeneShet, Omim, dbNSFPGene, PrimateAI, MGI, GenCC, ClinGen, DataVersions


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
    RefseqTranscript,
    GeneShet,
    HumanPhenotypeOntology,
]

class Command(BaseCommand):
    help = "Loads all reference data"

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration at http://data.omim.org/downloads")

    def handle(self, *args, **options):
        current_versions = dict(DataVersions.objects.values_list('data_model_name', 'version'))
        to_update = [
            model for model in REFERENCE_DATA_MODELS if current_versions.get(model.__name__) != model.CURRENT_VERSION
        ]
        updated = []
        update_failed = []

        if to_update[0] == GeneInfo:
            to_update = to_update[1:]

            # Download latest version first, and then add any genes from old releases not included in the latest release
            # Old gene ids are used in the gene constraint table and other datasets, as well as older sequencing data
            existing_gene_ids = set()
            existing_transcript_ids = set()
            new_transcripts = {}
            for gencode_release in GeneInfo.ALL_GENCODE_VERSIONS:
                new_transcripts.update(
                    GeneInfo.update_records(gencode_release, existing_gene_ids, existing_transcript_ids)
                )
            updated.append(GeneInfo.__name__)

            if new_transcripts:
                gene_id_map, _ = get_genes_by_id_and_symbol()
                TranscriptInfo.bulk_create_for_genes(new_transcripts, gene_id_map)

        for data_cls in to_update:
            data_model_name = data_cls.__name__
            try:
                data_cls.update_records(**options)
                updated.append(data_model_name)
            except Exception as e:
                logger.error("unable to update {}: {}".format(data_model_name, e))
                update_failed.append(data_model_name)

        logger.info("Done")
        if updated:
            logger.info("Updated: {}".format(', '.join(updated)))
        if update_failed:
            raise CommandError("Failed to Update: {}".format(', '.join(update_failed)))
