from aiohttp.web import HTTPBadRequest
import hail as hl
import os

VLM_DATA_DIR = os.environ.get('VLM_DATA_DIR')
SEQR_BASE_URL = os.environ.get('SEQR_BASE_URL')
VLM_DEFAULT_CONTACT_EMAIL = os.environ.get('VLM_DEFAULT_CONTACT_EMAIL')
NODE_ID = os.environ.get('NODE_ID')

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

def get_variant_match(query: dict) -> dict:
    chrom, pos, ref, alt, genome_build = _parse_match_query(query)
    locus = hl.locus(chrom, pos, reference_genome=genome_build)

    ac, hom = _get_variant_counts(locus, ref, alt, genome_build)

    liftover_genome_build = GENOME_VERSION_GRCh38 if genome_build == GENOME_VERSION_GRCh37 else GENOME_VERSION_GRCh37
    liftover_locus = hl.liftover(locus, liftover_genome_build)
    lift_ac, lift_hom = _get_variant_counts(liftover_locus, ref, alt, liftover_genome_build)

    url = _get_contact_url(
        chrom, pos, ref, alt, genome_build, liftover_genome_build, liftover_locus if lift_ac and not ac else None,
    )
    return _format_results(ac+lift_ac, hom+lift_hom, url)


def _get_contact_url(chrom: str, pos: int, ref: str, alt: str, genome_build: str, liftover_genome_build: str, liftover_locus: hl.LocusExpression) -> str:
    if VLM_DEFAULT_CONTACT_EMAIL:
        return f'mailto:{VLM_DEFAULT_CONTACT_EMAIL}'

    if liftover_locus is not None:
        lifted = hl.eval(liftover_locus)
        chrom = lifted.contig
        pos = lifted.position
        genome_build = liftover_genome_build
    genome_build = genome_build.replace('GRCh', '')
    return f'{SEQR_BASE_URL}summary_data/variant_lookup?genomeVersion={genome_build}&variantId={chrom}-{pos}-{ref}-{alt}'


def _parse_match_query(query: dict) -> tuple[str, int, str, str, str]:
    missing_params = [key for key in QUERY_PARAMS if key not in query]
    if missing_params:
        raise HTTPBadRequest(reason=f'Missing required parameters: {", ".join(missing_params)}')

    genome_build = ASSEMBLY_LOOKUP.get(query['assemblyId'])
    if not genome_build:
        raise HTTPBadRequest(reason=f'Invalid assemblyId: {query["assemblyId"]}')

    chrom = query['referenceName'].replace('chr', '')
    if genome_build == GENOME_VERSION_GRCh38:
        chrom = f'chr{chrom}'
    if not hl.eval(hl.is_valid_contig(chrom, reference_genome=genome_build)):
        raise HTTPBadRequest(reason=f'Invalid referenceName: {query["referenceName"]}')

    start = query['start']
    if not start.isnumeric():
        raise HTTPBadRequest(reason=f'Invalid start: {start}')
    start = int(start)
    if not hl.eval(hl.is_valid_locus(chrom, start, reference_genome=genome_build)):
        raise HTTPBadRequest(reason=f'Invalid start: {start}')

    return chrom, start, query['referenceBases'], query['alternateBases'], genome_build


def _get_variant_counts(locus: hl.LocusExpression, ref: str, alt: str, genome_build: str) -> hl.Struct:
    interval = hl.eval(hl.interval(locus, locus, includes_start=True, includes_end=True))
    ht = hl.read_table(
        f'{VLM_DATA_DIR}/{genome_build}/SNV_INDEL/annotations.ht', _intervals=[interval], _filter_intervals=True,
    )
    ht = ht.filter(ht.alleles == hl.array([ref, alt]))

    counts = ht.aggregate(hl.agg.take(ht.gt_stats, 1))
    return (counts[0].AC, counts[0].hom) if counts else (0, 0)


def _format_results(ac: int, hom: int, url: str) -> dict:
    total = ac - hom # Homozygotes count twice toward the total AC
    result_sets = [
        ('Homozygous', hom),
        ('Heterozygous', total - hom),
    ] if ac else []
    return {
        'beaconHandovers': [
            {
                'handoverType': BEACON_HANDOVER_TYPE,
                'url': url,
            }
        ],
        'meta': BEACON_META,
        'responseSummary': {
            'exists': bool(ac),
            'total': total
        },
        'response': {
            'resultSets': [
                {
                    'exists': True,
                    'id': f'{NODE_ID} {label}',
                    'results': [],
                    'resultsCount': count,
                    'setType': 'genomicVariant'
                } for label, count in result_sets
            ]
        }
    }
