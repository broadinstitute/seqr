import json
import logging
import redis
from collections import defaultdict

from seqr.models import SavedVariant, VariantSearchResults, Individual
from seqr.model_utils import _deprecated_retrieve_saved_variants_json
from seqr.utils.es_utils import get_es_variants_for_variant_tuples, InvalidIndexException
from seqr.utils.xpos_utils import get_chrom_pos
from settings import REDIS_SERVICE_HOSTNAME

logger = logging.getLogger(__name__)


def update_project_saved_variant_json(project, family_id=None):
    saved_variants = SavedVariant.objects.filter(family__project=project).select_related('family')
    if family_id:
        saved_variants = saved_variants.filter(family__family_id=family_id)

    saved_variants_map = {(v.xpos_start, v.ref, v.alt, v.family): v for v in saved_variants}
    variant_tuples = saved_variants_map.keys()
    saved_variants_map = {
        (xpos, ref, alt, family.guid): v for (xpos, ref, alt, family), v in saved_variants_map.items()
    }

    variants_json = _retrieve_saved_variants_json(project, variant_tuples)

    updated_saved_variant_guids = []
    for var in variants_json:
        for family_guid in var['familyGuids']:
            saved_variant = saved_variants_map.get((var['xpos'], var['ref'], var['alt'], family_guid))
            if saved_variant:
                _update_saved_variant_json(saved_variant, var)
                updated_saved_variant_guids.append(saved_variant.guid)

    return updated_saved_variant_guids


def reset_cached_search_results(project):
    try:
        redis_client = redis.StrictRedis(host=REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        keys_to_delete = []
        if project:
            result_guids = [res.guid for res in VariantSearchResults.objects.filter(families__project=project)]
            for guid in result_guids:
                keys_to_delete += redis_client.scan_iter(match='search_results__{}*'.format(guid))
        else:
            keys_to_delete = redis_client.keys(pattern='search_results__*')
        redis_client.delete(*keys_to_delete)
        logger.info('Reset {} cached results'.format(len(keys_to_delete)))
    except Exception as e:
        logger.error("Unable to reset cached search results: {}".format(e))


def _retrieve_saved_variants_json(project, variant_tuples, create_if_missing=False):
    xpos_ref_alt_tuples = []
    xpos_ref_alt_family_tuples = []
    family_id_to_guid = {}
    for xpos, ref, alt, family in variant_tuples:
        xpos_ref_alt_tuples.append((xpos, ref, alt))
        xpos_ref_alt_family_tuples.append((xpos, ref, alt, family.family_id))
        family_id_to_guid[family.family_id] = family.guid

    try:
        families = project.family_set.filter(guid__in=family_id_to_guid.values())
        return get_es_variants_for_variant_tuples(families, xpos_ref_alt_tuples)
    except InvalidIndexException:
        variants = _deprecated_retrieve_saved_variants_json(project, xpos_ref_alt_family_tuples, create_if_missing)
        for var in variants:
            var['familyGuids'] = [family_id_to_guid[var['extras']['family_id']]]
        return variants


def _update_saved_variant_json(saved_variant, saved_variant_json):
    saved_variant.saved_variant_json = saved_variant_json
    saved_variant.save()


# TODO process data before saving and then get rid of this
def variant_details(variant_json, project, user, individual_guids_by_id=None):
    if 'populations' in variant_json:
        return variant_json

    annotation = variant_json.get('annotation') or {}
    is_es_variant = annotation.get('db') == 'elasticsearch'

    chrom, pos = get_chrom_pos(variant_json['xpos'])

    extras = variant_json.get('extras') or {}
    genome_version = extras.get('genome_version') or '37'
    lifted_over_genome_version = '37' if genome_version == '38' else '38'
    coords_field = 'grch%s_coords' % lifted_over_genome_version
    coords = extras.get(coords_field).split('-') if extras.get(coords_field) else []
    lifted_over_chrom = coords[0].lstrip('chr') if len(coords) > 0 else ''
    lifted_over_pos = coords[1] if len(coords) > 1 else ''

    genotypes = {
        individual_id: {
            'ab': genotype.get('ab'),
            'ad': genotype.get('extras', {}).get('ad'),
            'cnvs': {
                'array': genotype.get('extras', {}).get('cnvs', {}).get('array'),
                'caller': genotype.get('extras', {}).get('cnvs', {}).get('caller'),
                'cn': genotype.get('extras', {}).get('cnvs', {}).get('cn'),
                'freq': genotype.get('extras', {}).get('cnvs', {}).get('freq'),
                'LRR_median': genotype.get('extras', {}).get('cnvs', {}).get('LRR_median'),
                'LRR_sd': genotype.get('extras', {}).get('cnvs', {}).get('LRR_sd'),
                'size': genotype.get('extras', {}).get('cnvs', {}).get('size'),
                'snps': genotype.get('extras', {}).get('cnvs', {}).get('snps'),
                'type': genotype.get('extras', {}).get('cnvs', {}).get('type'),
            },
            'dp': genotype.get('extras', {}).get('dp'),
            'gq': genotype.get('gq'),
            'numAlt': genotype.get('num_alt'),
            'pl': genotype.get('extras', {}).get('pl'),
            'sampleId': individual_id,
        } for individual_id, genotype in variant_json.get('genotypes', {}).items()
    }

    if not individual_guids_by_id:
        individual_guids_by_id = {i.individual_id: i.guid for i in Individual.objects.filter(family__project=project)}

    genotypes = {individual_guids_by_id.get(individual_id): genotype for individual_id, genotype in
                 genotypes.items()
                 if individual_guids_by_id.get(individual_id)}

    transcripts = defaultdict(list)
    for i, vep_a in enumerate(annotation['vep_annotation'] or []):
        transcripts[vep_a.get('gene', vep_a.get('gene_id'))].append(
            _transcript_detail(vep_a, i == annotation.get('worst_vep_annotation_index')))

    return {
        'chrom': chrom,
        'pos': pos,
        'predictions': {
            'cadd': annotation.get('cadd_phred'),
            'dann': annotation.get('dann_score'),
            'eigen': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'gerp_rs': annotation.get('GERP_RS'),
            'phastcons_100_vert': annotation.get('phastCons100way_vertebrate'),
            'mpc': annotation.get('mpc_score'),
            'metasvm': annotation.get('metasvm'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'primate_ai': annotation.get('primate_ai_score'),
            'revel': annotation.get('revel_score'),
            'sift': annotation.get('sift'),
            'splice_ai': annotation.get('splice_ai_delta_score'),
        },
        'mainTranscript': _variant_main_transcript(variant_json),
        'clinvar': {
            'clinicalSignificance': extras.get('clinvar_clinsig'),
            'variationId': extras.get('clinvar_variant_id'),
            'alleleId': extras.get('clinvar_allele_id'),
            'goldStars': extras.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class') if (user and user.is_staff) else None,
        },
        'genotypes': genotypes,
        'genotypeFilters': next((genotype.get('filter') for genotype in variant_json.get('genotypes', {}).values()), None),
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'originalAltAlleles': extras.get('orig_alt_alleles') or [],
        'populations': {
            'callset': {
                'af': annotation.get('freqs', {}).get('AF'),
                'ac': annotation.get('pop_counts', {}).get('AC'),
                'an': annotation.get('pop_counts', {}).get('AN'),
            },
            'topmed': {
                'af': annotation.get('freqs', {}).get('topmed_AF'),
                'ac': annotation.get('pop_counts', {}).get('topmed_AC'),
                'an': annotation.get('pop_counts', {}).get('topmed_AN'),
            },
            'g1k': {
                'af': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'ac': annotation.get('pop_counts', {}).get('g1kAC'),
                'an': annotation.get('pop_counts', {}).get('g1kAN'),
            },
            'exac': {
                'af': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'ac': annotation.get('pop_counts', {}).get('exac_v3_AC'),
                'an': annotation.get('pop_counts', {}).get('exac_v3_AN'),
                'hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
            },
            'gnomad_exomes': {
                'af': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax',
                                     annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_exomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
            },
            'gnomad_genomes': {
                'af': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
                'ac': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'an': annotation.get('pop_counts', {}).get('gnomad_genomes_AN'),
                'hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
        },
        'rsid': annotation.get('rsid'),
        'transcripts': transcripts,
    }


def _variant_main_transcript(variant_json):
    annotation = variant_json.get('annotation') or {}
    main_transcript = annotation.get('main_transcript') or (
        annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get(
            'worst_vep_annotation_index') is not None and annotation['vep_annotation'] else {})
    return _transcript_detail(main_transcript, True)


def _transcript_detail(transcript, isChosenTranscript):
    return {
        'transcriptId': transcript.get('feature') or transcript.get('transcript_id'),
        'transcriptRank': 0 if isChosenTranscript else transcript.get('transcript_rank', 100),
        'geneId': transcript.get('gene') or transcript.get('gene_id'),
        'geneSymbol': transcript.get('gene_symbol') or transcript.get('symbol'),
        'lof': transcript.get('lof'),
        'lofFlags': transcript.get('lof_flags'),
        'lofFilter': transcript.get('lof_filter'),
        'aminoAcids': transcript.get('amino_acids'),
        'biotype': transcript.get('biotype'),
        'canonical': transcript.get('canonical'),
        'cdnaPosition': transcript.get('cdna_position') or transcript.get('cdna_start'),
        'codons': transcript.get('codons'),
        'majorConsequence': transcript.get('consequence') or transcript.get('major_consequence'),
        'hgvsc': transcript.get('hgvsc'),
        'hgvsp': transcript.get('hgvsp'),
    }

