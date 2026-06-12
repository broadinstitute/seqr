from aiohttp import ClientSession
from aiohttp.web import HTTPBadRequest
from collections.abc import Callable
from datetime import datetime
import json
import os
from pyliftover.liftover import LiftOver
import re
from typing import Optional, Tuple

from vlm.clickhouse_utils import get_clickhouse_variant_counts, get_clickhouse_variant_details, CHROMOSOMES

SEQR_BASE_URL = os.environ.get('SEQR_BASE_URL')
VLM_DEFAULT_CONTACT_EMAIL = os.environ.get('VLM_DEFAULT_CONTACT_EMAIL')
NODE_ID = os.environ.get('NODE_ID')
LIFTOVER_DIR = f'{os.path.dirname(os.path.abspath(__file__))}/liftover_references'

ONTOLOGY_API_URL = 'https://ontology.jax.org/'

BEACON_HANDOVER_TYPE = {
    'id': NODE_ID,
    'label': f'{NODE_ID} browser'
}

BEACON_META = {
    'apiVersion': 'v1.0',
    'beaconId': 'com.gnx.beacon.v2',
}
VARIANT_SCHEMA = {
    'entityType': 'genomicVariant',
    'schema': 'ga4gh-beacon-variant-v2.0.0'
}
PHENOPACKET_SCHEMA = {
    'entityType': 'Family',
    'schema': 'phenopacket-2.0',
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

MIN_POS = 1
MAX_POS = 300_000_000


async def get_variant_match(query: dict) -> dict:
    return await _get_variant_match(query, get_match=get_clickhouse_variant_counts, get_results=_get_match_results)


async  def get_variant_match_details(query: dict) -> dict:
    return await _get_variant_match(query, get_match=get_clickhouse_variant_details, get_results=_get_match_detail_results)


async def _get_variant_match(query: dict, get_match: Callable, get_results: Callable) -> dict:
    chrom, pos, ref, alt, genome_build = _parse_match_query(query)

    match = get_match(chrom, pos, genome_build, ref, alt)
    liftover = _liftover_variant(chrom, pos, genome_build)
    lift_match = get_match(*liftover, ref, alt) if liftover else None

    url = _get_contact_url(
        chrom, pos, ref, alt, genome_build, liftover if lift_match and not match else None,
    )
    total, results_set, schema = await get_results(match, lift_match)
    return _format_results(total, results_set, url, schema)


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


async def _get_match_results(match: Optional[Tuple[int, int]], lift_match: Optional[Tuple[int, int]]) -> Tuple[int, list[dict]]:
    build_ac, build_hom = match or (0, 0)
    lift_ac, lift_hom = lift_match or (0, 0)
    ac = build_ac + lift_ac
    hom = build_hom + lift_hom
    total = ac - hom  # Homozygotes count twice toward the total AC
    result_sets = [
        ('Homozygous', hom, []),
        ('Heterozygous', total - hom, []),
        ('Hemizygous', 0, []),
        ('Unknown', 0, []),
    ]
    return total, result_sets, VARIANT_SCHEMA


SEX_LOOKUP = {'M': 'MALE', 'F': 'FEMALE', 'U': 'UNKNOWN_SEX'}
AFFECTED_LOOKUP = {'A': 'AFFECTED', 'N': 'UNAFFECTED', 'U': 'MISSING'}
GT_LOOKUP = {
    'HET': {'id': 'GENO:0000135', 'label': 'heterozygous'},
    'HOM': {'id': 'GENO:0000136', 'label': 'homozygous'},
}

GENO_RESOURCE = {
    'id': 'geno',
    'name': 'GENO ontology',
    'url': 'http://purl.obolibrary.org/obo/geno.owl',
    'version': '2026-02-02',
    'namespacePrefix': 'GENO',
    'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
}
HPO_RESOURCE = {
    'id': 'hp',
    'name': 'Human Phenotype Ontology',
    'url': 'http://purl.obolibrary.org/obo/hp.owl',
    'namespacePrefix': 'HP',
    'iriPrefix': 'http://purl.obolibrary.org/obo/HP_',
}
OMIM_RESOURCE = {
    'id': 'omim',
    'name': 'Online Mendelian Inheritance in Man',
    'url': 'https://www.omim.org',
    'namespacePrefix': 'OMIM',
    'iriPrefix': 'https://www.omim.org/entry/',
}
MONDO_RESOURCE = {
    'id': 'mondo',
    'name': 'Mondo Disease Ontology',
    'url': 'http://purl.obolibrary.org/obo/mondo.owl',
    'namespacePrefix': 'MONDO',
    'iriPrefix': 'http://purl.obolibrary.org/obo/MONDO_',
}


async def _get_match_detail_results(match: list[tuple], lift_match: list[tuple]) -> Tuple[int, list[dict]]:
    results = []
    hpo_label_map = {}
    mondo_label_map = {}
    async with ClientSession(ONTOLOGY_API_URL) as session:
        for f_i, (samples, has_discovery, has_excluded) in enumerate(match + (lift_match or [])):
            family_id = f'F_{f_i}'
            proband = None
            relatives = []
            pedigree = []
            for s_i, (affected, sex, *sample) in enumerate(samples):
                individual_id = f'I_{f_i}_{s_i}'
                sex = SEX_LOOKUP.get(sex, 'OTHER_SEX')
                pedigree.append({
                    'family_id': family_id,
                    'individual_id': individual_id,
                    'paternal_id': '0',
                    'maternal_id': '0',
                    'sex': sex,
                    'affected_status': AFFECTED_LOOKUP[affected],
                })

                phenopacket = await _format_phenopacket(
                    hpo_label_map, mondo_label_map, session, individual_id, has_discovery, has_excluded, sex, *sample,
                )
                if affected == 'A' and proband is None:
                    proband = phenopacket
                else:
                    relatives.append(phenopacket)

            if not proband:
                # TODO test
                proband = relatives[0]
                relatives = relatives[1:]

            results.append({
                'id': family_id,
                'proband': proband,
                'relatives': relatives,
                'pedigree': {'persons': pedigree},
                'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
            })

    result_sets = [
        (None, len(results), results),
    ]
    return len(results), result_sets, PHENOPACKET_SCHEMA


async def _format_phenopacket(
    hpo_label_map, mondo_label_map, session, individual_id, has_discovery, has_excluded, sex, gt, omim_label, omim_id,
    mondo_id, features, is_solved, vlm_contact_email, restrict_sharing,
):
    if restrict_sharing:
        features = None
        omim_id = None
        mondo_id = None
        is_solved = False

    resources = [GENO_RESOURCE]
    phenotypic_features = []
    if features:
        for feature in json.loads(features):
            hpo_id = feature['id']
            if hpo_id not in hpo_label_map:
                async with session.get(f'/api/hp/terms/{hpo_id}') as resp:
                    hpo_label_map[hpo_id] = (await resp.json())['name']
            phenotypic_features.append({'id': hpo_id, 'label': hpo_label_map[hpo_id]})
        resources.append({**HPO_RESOURCE, 'version': datetime.now().strftime('%Y-%m-%d')})
    interpretation = {
        'subject_or_biosample_id': individual_id,
        'interpretation_status': 'CANDIDATE' if has_discovery else ('REJECTED' if has_excluded else 'UNKNOWN_STATUS'),
        'call': {'variation_descriptor': {'allelic_state': GT_LOOKUP[gt]}},
    }
    diagnosis = {'genomic_interpretations': [interpretation]}
    if omim_id:
        diagnosis['disease'] = {'id': f'OMIM:{omim_id}', 'label': omim_label}
        resources.append({**OMIM_RESOURCE, 'version': datetime.now().strftime('%Y-%m-%d')})
    elif mondo_id:
        if mondo_id not in mondo_label_map:
            async with session.get(f'/api/mondo/terms/{mondo_id}') as resp:
                mondo_label_map[mondo_id] = (await resp.json())['name']
        diagnosis['disease'] = {'id': mondo_id, 'label': mondo_label_map[mondo_id]}
        resources.append({**MONDO_RESOURCE, 'version': datetime.now().strftime('%Y-%m-%d')})

    return {
        'id': individual_id,
        'subject': {'id': individual_id, 'sex': sex},
        'phenotypic_features': phenotypic_features,
        'interpretations': [{
            'id': individual_id,
            'progress_status': 'SOLVED' if is_solved else 'UNKNOWN_PROGRESS',
            'diagnosis': diagnosis,
        }],
        'meta_data': {
            'phenopacket_schema_version': '2.0',
            'submitted_by': vlm_contact_email,
            'resources': resources,
        },
    }


def _format_results(total: int, result_sets: list[dict], url: str, schema: dict) -> dict:
    return {
        'beaconHandovers': [
            {
                'handoverType': BEACON_HANDOVER_TYPE,
                'url': url,
                'email': VLM_DEFAULT_CONTACT_EMAIL,
            }
        ],
        'meta': {
            **BEACON_META,
            'returnedSchemas': [schema],
        },
        'responseSummary': {
            'exists': bool(total),
            'total': total
        },
        'response': {
            'resultSets': [
                {
                    'exists': bool(count),
                    'id': f'{NODE_ID} {label}' if label else NODE_ID,
                    'results': results,
                    'resultsCount': count,
                    'setType': schema['entityType'],
                } for label, count, results in result_sets
            ],
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
