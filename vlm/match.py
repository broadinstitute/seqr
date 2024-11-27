from aiohttp.web import HTTPBadRequest
import hail as hl
import os

VLM_DATA_DIR = os.environ.get('VLM_DATA_DIR')
SEQR_BASE_URL = os.environ.get('SEQR_BASE_URL')
NODE_ID = os.environ.get('NODE_ID', 'Broad seqr')

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
    key_table = hl.Table.parallelize([
        hl.struct(
            locus=hl.locus(chrom, pos, reference_genome=genome_build),
            alleles=[ref, alt],
        )
    ]).key_by('locus', 'alleles')
    query_result = hl.query_table(
        f'{VLM_DATA_DIR}/{genome_build}/SNV_INDEL/annotations.ht',
        key_table.key,
    ).first().drop(*key_table.key)
    ht = key_table.annotate(gt_stats=query_result.gt_stats)
    counts = ht.aggregate(hl.agg.take(ht.gt_stats, 1))[0]

    return _format_results(counts, genome_build, f'{chrom}-{pos}-{ref}-{alt}')


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


def _format_results(counts: hl.Struct, genome_build: str, variant_id: str) -> dict:
    result_sets = [] if counts is None else [
        ('Homozygous', counts.hom),
        ('Heterozygous', counts.AC - counts.hom),
    ]
    return {
        'beaconHandovers': [
            {
                'handoverType': BEACON_HANDOVER_TYPE,
                'url': f'{SEQR_BASE_URL}summary_data/variant_lookup?genomeVersion={genome_build.replace("GRCh", "")}&variantId={variant_id}',
            }
        ],
        'meta': BEACON_META,
        'responseSummary': {
            'exists': bool(counts),
            'total': 0 if counts is None else counts.AC,
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
