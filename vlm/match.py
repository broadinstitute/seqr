from aiohttp.web import HTTPBadRequest
from collections.abc import Callable
import os
from pyliftover.liftover import LiftOver
import re
from typing import Optional, Tuple

from vlm.clickhouse_utils import get_clickhouse_variant_counts

SEQR_BASE_URL = os.environ.get('SEQR_BASE_URL')
VLM_DEFAULT_CONTACT_EMAIL = os.environ.get('VLM_DEFAULT_CONTACT_EMAIL')
NODE_ID = os.environ.get('NODE_ID')
LIFTOVER_DIR = f'{os.path.dirname(os.path.abspath(__file__))}/liftover_references'

BEACON_HANDOVER_TYPE = {
    'id': NODE_ID,
    'label': f'{NODE_ID} browser'
}

BEACON_META = {
    'apiVersion': 'v1.0',
    'beaconId': 'com.gnx.beacon.v2',
    'returnedSchemas': [
        {
            'entityType': 'genomicVariant',
            'schema': 'ga4gh-beacon-variant-v2.0.0'
        }
    ]
}

QUERY_PARAMS = ['assemblyId', 'referenceName', 'start', 'referenceBases', 'alternateBases']

GENOME_VERSION_GRCh38 = 'GRCh38'
GENOME_VERSION_GRCh37 = 'GRCh37'
ASSEMBLY_LOOKUP = {
    GENOME_VERSION_GRCh37: GENOME_VERSION_GRCh37,
    GENOME_VERSION_GRCh38: GENOME_VERSION_GRCh38,
    'hg38': GENOME_VERSION_GRCh38,
    'hg19': GENOME_VERSION_GRCh37,
}

CHROMOSOMES = {
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
    '20', '21', '22', 'X', 'Y', 'M',
}
MIN_POS = 1
MAX_POS = 300_000_000


def get_variant_match(query: dict) -> dict:
    return _get_variant_match(query, get_match=get_clickhouse_variant_counts, get_results=_get_match_results)


def _get_variant_match(query: dict, get_match: Callable, get_results: Callable) -> dict:
    chrom, pos, ref, alt, genome_build = _parse_match_query(query)

    match = get_match(chrom, pos, genome_build, ref, alt)
    liftover = _liftover_variant(chrom, pos, genome_build)
    lift_match = get_match(*liftover, ref, alt) if liftover else None

    url = _get_contact_url(
        chrom, pos, ref, alt, genome_build, liftover if lift_match and not match else None,
    )
    total, results_set = get_results(match, lift_match)
    return _format_results(total, results_set, url)


def _get_contact_url(chrom: str, pos: int, ref: str, alt: str, genome_build: str, liftover: Optional[Tuple[str, int, str]]) -> str:
    if not SEQR_BASE_URL:
        return SEQR_BASE_URL

    if liftover is not None:
        chrom, pos, genome_build = liftover
    genome_build = genome_build.replace('GRCh', '')
    return f'{SEQR_BASE_URL}variant_lookup?genomeVersion={genome_build}&variantId={chrom}-{pos}-{ref}-{alt}'


def _parse_match_query(query: dict) -> tuple[str, int, str, str, str]:
    missing_params = [key for key in QUERY_PARAMS if key not in query]
    if missing_params:
        raise HTTPBadRequest(reason=f'Missing required parameters: {", ".join(missing_params)}')

    genome_build = ASSEMBLY_LOOKUP.get(query['assemblyId'])
    if not genome_build:
        raise HTTPBadRequest(reason=f'Invalid assemblyId: {query["assemblyId"]}')

    chrom = query['referenceName'].replace('chr', '')
    if chrom not in CHROMOSOMES:
        raise HTTPBadRequest(reason=f'Invalid referenceName: {query["referenceName"]}')

    start = query['start']
    if not start.isnumeric():
        raise HTTPBadRequest(reason=f'Invalid start: {start}')
    start = int(start)
    if start < MIN_POS or start > MAX_POS:
        raise HTTPBadRequest(reason=f'Invalid start: {start}')

    for allele_field in ['referenceBases', 'alternateBases']:
        allele = query[allele_field]
        if not re.fullmatch(r'[ATCG]', allele):
            raise HTTPBadRequest(reason=f'Invalid {allele_field}: {allele}')

    return chrom, start, query['referenceBases'], query['alternateBases'], genome_build


def _get_match_results(match: Optional[Tuple[int, int]], lift_match: Optional[Tuple[int, int]]) -> Tuple[int, list[dict]]:
    build_ac, build_hom = match or (0, 0)
    lift_ac, lift_hom = lift_match or (0, 0)
    ac = build_ac + lift_ac
    hom = build_hom + lift_hom
    total = ac - hom  # Homozygotes count twice toward the total AC
    results = [
        ('Homozygous', hom),
        ('Heterozygous', total - hom),
        ('Hemizygous', 0),
        ('Unknown', 0),
    ]
    result_sets = [
        {
            'exists': bool(count),
            'id': f'{NODE_ID} {label}',
            'results': [],
            'resultsCount': count,
            'setType': 'genomicVariant'
        } for label, count in results
    ]
    return total, result_sets


def _format_results(total: int, result_sets: list[dict], url: str) -> dict:
    return {
        'beaconHandovers': [
            {
                'handoverType': BEACON_HANDOVER_TYPE,
                'url': url,
                'email': VLM_DEFAULT_CONTACT_EMAIL,
            }
        ],
        'meta': BEACON_META,
        'responseSummary': {
            'exists': bool(total),
            'total': total
        },
        'response': {
            'resultSets': result_sets,
        }
    }


LIFTOVERS = {
    GENOME_VERSION_GRCh38: None,
    GENOME_VERSION_GRCh37: None,
}


def _liftover_variant(chrom: str, pos: int, genome_build: str) -> Optional[Tuple[str, int, str]]:
    liftover_genome_build = GENOME_VERSION_GRCh38 if genome_build == GENOME_VERSION_GRCh37 else GENOME_VERSION_GRCh37
    if not LIFTOVERS[genome_build]:
        LIFTOVERS[genome_build] = LiftOver(
            f'{LIFTOVER_DIR}/{genome_build.lower()}_to_{liftover_genome_build.lower()}.over.chain.gz'
        )
    lifted_coord = LIFTOVERS[genome_build].convert_coordinate(f'chr{chrom}', pos)
    return (lifted_coord[0][0].replace('chr', ''), lifted_coord[0][1], liftover_genome_build) if lifted_coord and lifted_coord[0] else None
