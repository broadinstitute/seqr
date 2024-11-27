from aiohttp.web import HTTPBadRequest
import hail as hl
import os

VLM_DATA_DIR = os.environ.get('VLM_DATA_DIR')

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
    variant_key, genome_build = _parse_match_query(query)
    key_table = hl.Table.parallelize([variant_key]).key_by('locus', 'alleles')
    query_result = hl.query_table(
        f'{VLM_DATA_DIR}/{genome_build}/SNV_INDEL/annotations.ht',
        key_table.key,
    ).first().drop(*key_table.key)

    ht = key_table.annotate(gt_stats=query_result.gt_stats)
    counts = ht.aggregate(hl.agg.take(ht.gt_stats, 1))[0]

    return {'found': False} if counts is None else dict(counts)

def _parse_match_query(query: dict) -> tuple[hl.StructExpression, str]:
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

    return hl.struct(
        locus=hl.locus(chrom, start, reference_genome=genome_build),
        alleles=[query['referenceBases'], query['alternateBases']],
    ), genome_build
