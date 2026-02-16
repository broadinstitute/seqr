import dataclasses
import hashlib
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
import time
from typing import Literal, Union, Optional
from urllib3.util.retry import Retry

from django.db.models import Max
from django.core.management.base import BaseCommand

from clickhouse_search.models.search_models import (
    EntriesGRCh37SnvIndel,
    EntriesSnvIndel,
    VariantDetailsGRCh37SnvIndel,
    VariantDetailsSnvIndel,
)
from reference_data.models import DataVersions
from reference_data.models import GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38
from seqr.utils.communication_utils import safe_post_to_slack
from settings import (
    CLINGEN_ALLELE_REGISTRY_LOGIN,
    CLINGEN_ALLELE_REGISTRY_PASSWORD,
    SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
)

logger = logging.getLogger(__name__)

ALLELE_REGISTRY_GNOMAD_IDS = {
    GENOME_VERSION_GRCh37: "gnomAD_2",
    GENOME_VERSION_GRCh38: "gnomAD_4",
}
ALLELE_REGISTRY_HEADERS = {
    GENOME_VERSION_GRCh37: [
        "##fileformat=VCFv4.2",
        "##contig=<ID=1,length=249250621,assembly=GRCh37>",
        "##contig=<ID=2,length=243199373,assembly=GRCh37>",
        "##contig=<ID=3,length=198022430,assembly=GRCh37>",
        "##contig=<ID=4,length=191154276,assembly=GRCh37>",
        "##contig=<ID=5,length=180915260,assembly=GRCh37>",
        "##contig=<ID=6,length=171115067,assembly=GRCh37>",
        "##contig=<ID=7,length=159138663,assembly=GRCh37>",
        "##contig=<ID=8,length=146364022,assembly=GRCh37>",
        "##contig=<ID=9,length=141213431,assembly=GRCh37>",
        "##contig=<ID=10,length=135534747,assembly=GRCh37>",
        "##contig=<ID=11,length=135006516,assembly=GRCh37>",
        "##contig=<ID=12,length=133851895,assembly=GRCh37>",
        "##contig=<ID=13,length=115169878,assembly=GRCh37>",
        "##contig=<ID=14,length=107349540,assembly=GRCh37>",
        "##contig=<ID=15,length=102531392,assembly=GRCh37>",
        "##contig=<ID=16,length=90354753,assembly=GRCh37>",
        "##contig=<ID=17,length=81195210,assembly=GRCh37>",
        "##contig=<ID=18,length=78077248,assembly=GRCh37>",
        "##contig=<ID=19,length=59128983,assembly=GRCh37>",
        "##contig=<ID=20,length=63025520,assembly=GRCh37>",
        "##contig=<ID=21,length=48129895,assembly=GRCh37>",
        "##contig=<ID=22,length=51304566,assembly=GRCh37>",
        "##contig=<ID=X,length=155270560,assembly=GRCh37>",
        "##contig=<ID=Y,length=59373566,assembly=GRCh37>",
        "##contig=<ID=MT,length=16569,assembly=GRCh37>",
        "#CHROM POS ID  REF ALT QUAL    FILTER  INFO",
    ],
    GENOME_VERSION_GRCh38: [
        "##fileformat=VCFv4.2",
        "##contig=<ID=1,length=248956422,assembly=GRCh38>",
        "##contig=<ID=2,length=242193529,assembly=GRCh38>",
        "##contig=<ID=3,length=198295559,assembly=GRCh38>",
        "##contig=<ID=4,length=190214555,assembly=GRCh38>",
        "##contig=<ID=5,length=181538259,assembly=GRCh38>",
        "##contig=<ID=6,length=170805979,assembly=GRCh38>",
        "##contig=<ID=7,length=159345973,assembly=GRCh38>",
        "##contig=<ID=8,length=145138636,assembly=GRCh38>",
        "##contig=<ID=9,length=138394717,assembly=GRCh38>",
        "##contig=<ID=10,length=133797422,assembly=GRCh38>",
        "##contig=<ID=11,length=135086622,assembly=GRCh38>",
        "##contig=<ID=12,length=133275309,assembly=GRCh38>",
        "##contig=<ID=13,length=114364328,assembly=GRCh38>",
        "##contig=<ID=14,length=107043718,assembly=GRCh38>",
        "##contig=<ID=15,length=101991189,assembly=GRCh38>",
        "##contig=<ID=16,length=90338345,assembly=GRCh38>",
        "##contig=<ID=17,length=83257441,assembly=GRCh38>",
        "##contig=<ID=18,length=80373285,assembly=GRCh38>",
        "##contig=<ID=19,length=58617616,assembly=GRCh38>",
        "##contig=<ID=20,length=64444167,assembly=GRCh38>",
        "##contig=<ID=21,length=46709983,assembly=GRCh38>",
        "##contig=<ID=22,length=50818468,assembly=GRCh38>",
        "##contig=<ID=X,length=156040895,assembly=GRCh38>",
        "##contig=<ID=Y,length=57227415,assembly=GRCh38>",
        "##contig=<ID=M,length=16569,assembly=GRCh38>",
        "#CHROM POS ID  REF ALT QUAL    FILTER  INFO",
    ],
}
ALLELE_REGISTRY_URL = "https://reg.genome.network/alleles?file=vcf&fields=none+@id+genomicAlleles+externalRecords.{}.id"
HTTP_REQUEST_TIMEOUT_S = 420
VCF_DEFAULT_VALUE = "."


@dataclasses.dataclass
class AlleleRegistryError:
    error_type: str
    description: str
    message: str
    input_line: Optional[str]

    @classmethod
    def from_api_response(cls, response: dict):
        return cls(
            error_type=response["errorType"],
            description=response["description"],
            message=response["message"],
            input_line=response.get("inputLine"),
        )

    def __str__(self) -> str:
        msg = (
            f"\nTYPE: {self.error_type}"
            f"\nDESCRIPTION: {self.description}\nMESSAGE: {self.message}"
        )
        return (
            msg if self.input_line is None else f"{msg}\nINPUT_LINE: {self.input_line}"
        )


def requests_retry_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods={"PUT"},
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def build_url(
    genome_version: Literal[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38],
) -> str:
    login = CLINGEN_ALLELE_REGISTRY_LOGIN
    password = CLINGEN_ALLELE_REGISTRY_PASSWORD
    base_url = ALLELE_REGISTRY_URL.format(ALLELE_REGISTRY_GNOMAD_IDS[genome_version])

    # Adapted from https://reg.clinicalgenome.org/doc/scripts/request_with_payload.py
    identity = hashlib.sha1(f"{login}{password}".encode("utf-8")).hexdigest()  # nosec
    gb_time = str(int(time.time()))
    token = hashlib.sha1(f"{base_url}{identity}{gb_time}".encode("utf-8")).hexdigest()  # nosec
    return f"{base_url}&gbLogin={login}&gbTime={gb_time}&gbToken={token}"


def handle_api_response(
    genome_version: Literal[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38],
    response: requests.Response,
) -> dict[str, str]:
    response_json = response.json()
    if not response.ok or "errorType" in response_json:
        error = AlleleRegistryError.from_api_response(response_json)
        logger.error(error)
        raise HTTPError(error.message)
    elif not isinstance(response_json, list):
        raise HTTPError(f"Unexpected AR response type: {type(response_json)}")

    mapped_variants, errors, unmapped_variants = {}, [], []
    for allele_response in response_json:
        if "errorType" in allele_response:
            errors.append(
                AlleleRegistryError.from_api_response(allele_response),
            )
            continue

        # Extract CAID and allele info
        try:
            caid = allele_response["@id"].split("/")[-1]
            allele_info = next(
                record
                for record in allele_response["genomicAlleles"]
                if record["referenceGenome"] == f"GRCh{genome_version}"
            )
            chrom = allele_info["chromosome"]
            pos = allele_info["coordinates"][0]["end"]
            ref = allele_info["coordinates"][0]["referenceAllele"]
            alt = allele_info["coordinates"][0]["allele"]
        except (KeyError, StopIteration):
            unmapped_variants.append(allele_response)
            continue

        if ref == "" or alt == "":
            # AR will turn alleles like ["A","ATT"] to ["", "TT"] so try using gnomad IDs instead
            if "externalRecords" in allele_response:
                gnomad_id = allele_response["externalRecords"][
                    ALLELE_REGISTRY_GNOMAD_IDS[genome_version]
                ][0]["id"]
                parts = gnomad_id.split("-")
                if len(parts) != 4:
                    unmapped_variants.append(allele_response)
                    continue
                chrom, pos, ref, alt = parts
            else:
                unmapped_variants.append(allele_response)
                continue

        if chrom == 'MT':
            chrom = 'M'
        mapped_variants[f"{chrom}-{pos}-{ref}-{alt}"] = caid
    logger.info(
        f"{len(response_json) - len(errors)} out of {len(response_json)} variants returned CAID(s)",
    )
    if unmapped_variants:
        logger.info(
            f"{len(unmapped_variants)} registered variant(s) cannot be mapped back to ours. "
            f"\nFirst unmappable variant:\n{unmapped_variants[0]}",
        )
    if errors:
        logger.warning(
            f"{len(errors)} failed. First error: {errors[0]}",
        )
    return mapped_variants


def register_caids(
    genome_version: Literal[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38],
    variants: Union[list[VariantDetailsGRCh37SnvIndel], list[VariantDetailsSnvIndel]],
) -> int:
    rows = list(ALLELE_REGISTRY_HEADERS[genome_version]) # NB: new copy of the list
    for variant in variants:
        chrom, pos, ref, alt = variant.variant_id.split("-")
        chrom = chrom.replace(
            "chr", ""
        )  # NB: The Allele Registry does not accept contigs prefixed with 'chr', even for GRCh38
        rows.append(
            "\t".join(
                [
                    chrom,
                    pos,
                    VCF_DEFAULT_VALUE,
                    ref,
                    alt,
                    VCF_DEFAULT_VALUE,
                    VCF_DEFAULT_VALUE,
                    VCF_DEFAULT_VALUE,
                ]
            )
        )
    data = "\n".join(rows) + "\n"
    s = requests_retry_session()
    res = s.put(
        url=build_url(genome_version),
        data=data,
        timeout=HTTP_REQUEST_TIMEOUT_S,
    )
    mapped_variants = handle_api_response(genome_version, res)
    max_key_id = -1
    for variant in variants:
        variant.caid = mapped_variants.get(variant.variant_id, None)
        max_key_id = max(max_key_id, variant.key_id)
    return max_key_id


class Command(BaseCommand):
    help = "Register newly loaded seqr variants with the Clingen Allele Registry"
    batch_size = 10_000

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=self.batch_size,
            help="Number of variants to process per batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        for genome_version, variant_details_model, entries_model in [
            (GENOME_VERSION_GRCh37, VariantDetailsGRCh37SnvIndel, EntriesGRCh37SnvIndel),
            (GENOME_VERSION_GRCh38, VariantDetailsSnvIndel, EntriesSnvIndel),
        ]:
            version_obj = DataVersions.objects.filter(
                data_model_name=f"{genome_version}/ClingenAlleleRegistry"
            ).first()

            if not version_obj:
                max_key_id = entries_model.objects.aggregate(max_key=Max("key_id"))["max_key"] or 0
                version_obj = DataVersions(
                    data_model_name=f"{genome_version}/ClingenAlleleRegistry",
                    version=str(max_key_id),
                )
                version_obj.save()

            min_key = curr_key = max_key = int(version_obj.version)
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
                    variant_details_model.objects.using('clickhouse_write').bulk_update(variants, ["caid"])
                except Exception:
                    logger.exception(
                        f"Failed in {genome_version}/ClingenAlleleRegistry curr_key: {curr_key}"
                    )
                    break

                # Save current key on every iteration
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
