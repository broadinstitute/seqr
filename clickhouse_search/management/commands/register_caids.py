import logging
from typing import Union

from django.core.management.base import BaseCommand, CommandError

from clickhouse_search.models.search_models import (
    VariantDetailsGRCh37SnvIndel,
    VariantDetailsSnvIndel,
)
from reference_data.models import DataVersions
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.utils.communication_utils import safe_post_to_slack
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)


def register_caids(
    genome_version: str,
    variants: list[Union[VariantDetailsGRCh37SnvIndel, VariantDetailsSnvIndel]],
) -> int:
    # Todo, implement registration.
    return max(v.key_id for v in variants)


class Command(BaseCommand):
    help = "Register newly loaded seqr variants with the Clingen Allele Registry"
    batch_size = 20_000

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=self.batch_size,
            help="Number of variants to process per batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        for genome_version, variant_details_model in [
            (GENOME_VERSION_GRCh37, VariantDetailsGRCh37SnvIndel),
            (GENOME_VERSION_GRCh38, VariantDetailsSnvIndel),
        ]:
            version_obj = DataVersions.objects.filter(
                data_model_name=f"{genome_version}/ClingenAlleleRegistry"
            ).first()

            # Key must exist
            if not version_obj:
                raise CommandError(
                    f"An existing CAID data version is required for genome version {genome_version}"
                )

            # Key must be integer
            try:
                min_key = curr_key = max_key = int(version_obj.version)
            except (TypeError, ValueError):
                raise CommandError(
                    f"DataVersions.version for {genome_version}/ClingenAlleleRegistry "
                    f"must be an integer, got {version_obj.version!r}"
                )

            while True:
                qs = variant_details_model.objects.join_series(
                    curr_key + 1,
                    curr_key + 1 + batch_size,
                )
                variants = list(qs)
                if not variants:
                    break

                try:
                    max_key = register_caids(genome_version, variants)
                except Exception:
                    logger.exception(
                        f"Failed in {genome_version}/ClingenAlleleRegistry batch {curr_key}"
                    )
                    break

                # Save curr on every iteration
                curr_key = max_key
                version_obj.version = curr_key
                version_obj.save()

            if min_key != max_key:
                slack_message = (
                    f"Successfully called {genome_version}/ClingenAlleleRegistry "
                    f"for variants {min_key} -> {max_key}."
                )
                safe_post_to_slack(
                    SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
                    slack_message,
                )
