import json
import logging
from collections import defaultdict
from django.contrib.auth.models import User

from seqr.models import SavedVariant, Sample
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
from xbrowse_server.base.models import Project as BaseProject
from xbrowse_server.base.lookups import get_variants_from_variant_tuples


def get_or_create_saved_variant(xpos=None, ref=None, alt=None, family=None, project=None, **kwargs):
    if not project:
        project = family.project
    saved_variant, _ = SavedVariant.objects.get_or_create(
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        project=project,
    )
    if not saved_variant.saved_variant_json:
        try:
            saved_variants_json = _retrieve_saved_variants_json(project, [(xpos, ref, alt, family.family_id)], create_if_missing=True)
            if len(saved_variants_json):
                _update_saved_variant_json(saved_variant, saved_variants_json[0])
        except Exception as e:
            logging.error("Unable to retrieve variant annotations for %s (%s, %s, %s): %s" % (family, xpos, ref, alt, e))
    return saved_variant


def update_project_saved_variant_json(project, family_id=None):
    saved_variants = SavedVariant.objects.filter(project=project, family__isnull=False).select_related('family')
    if family_id:
        saved_variants = saved_variants.filter(family__family_id=family_id)
    saved_variants_map = {(v.xpos_start, v.ref, v.alt, v.family.family_id): v for v in saved_variants}

    variants_json = _retrieve_saved_variants_json(project, saved_variants_map.keys())

    updated_saved_variant_guids = []
    for var in variants_json:
        saved_variant = saved_variants_map[(var['xpos'], var['ref'], var['alt'], var['extras']['family_id'])]
        _update_saved_variant_json(saved_variant, var)
        updated_saved_variant_guids.append(saved_variant.guid)

    return updated_saved_variant_guids


def _retrieve_saved_variants_json(project, variant_tuples, create_if_missing=False):
    project_id = project.deprecated_project_id
    xbrowse_project = BaseProject.objects.get(project_id=project_id)
    user = User.objects.filter(is_staff=True).first()  # HGMD annotations are only returned for staff users

    variants = get_variants_from_variant_tuples(xbrowse_project, variant_tuples, user=user)
    if not create_if_missing:
        variants = [var for var in variants if not var.get_extra('created_variant')]
    add_extra_info_to_variants_project(get_reference(), xbrowse_project, variants, add_populations=True)
    return [variant.toJSON() for variant in variants]


def _update_saved_variant_json(saved_variant, saved_variant_json):
    saved_variant.saved_variant_json = json.dumps(saved_variant_json)
    saved_variant.save()


# TODO once variant search is rewritten saved_variant_json shouldn't need any postprocessing

def variant_details(variant_json, project, user=None, individual_guids_by_id=None, sample_guids_by_id=None):
    annotation = variant_json.get('annotation') or {}
    main_transcript = variant_main_transcript(variant_json)
    is_es_variant = annotation.get('db') == 'elasticsearch'

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
            'alleles': genotype.get('alleles', []),
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
            'filter': genotype.get('filter'),
            'gq': genotype.get('gq'),
            'numAlt': genotype.get('num_alt'),
            'pl': genotype.get('extras', {}).get('pl'),
        } for individual_id, genotype in variant_json.get('genotypes', {}).items()
    }
    if individual_guids_by_id:
        genotypes = {individual_guids_by_id.get(individual_id): genotype for individual_id, genotype in genotypes.items()}
    else:
        if not sample_guids_by_id:
            samples = Sample.objects.filter(
                individual__family__project=project,
                individual__individual_id__in=genotypes.keys(),
                loaded_date__isnull=False,
                dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS
            ).order_by('loaded_date').prefetch_related('individual')
            sample_guids_by_id = {s.individual.individual_id: s.guid for s in samples}
        genotypes = {sample_guids_by_id.get(individual_id): genotype for individual_id, genotype in genotypes.items()
                     if sample_guids_by_id.get(individual_id)}

    transcripts = defaultdict(list)
    for i, vep_a in enumerate(annotation.get('vep_annotation') or []):
        transcripts[vep_a.get('gene', vep_a.get('gene_id'))].append({
            'transcriptId': vep_a.get('feature') or vep_a.get('transcript_id'),
            'isChosenTranscript': i == annotation.get('worst_vep_annotation_index'),
            'aminoAcids': vep_a.get('amino_acids'),
            'canonical': vep_a.get('canonical'),
            'cdnaPosition': vep_a.get('cdna_position') or vep_a.get('cdna_start'),
            'cdsPosition': vep_a.get('cds_position'),
            'codons': vep_a.get('codons'),
            'consequence': vep_a.get('consequence') or vep_a.get('major_consequence'),
            'hgvsc': vep_a.get('hgvsc'),
            'hgvsp': vep_a.get('hgvsp'),
        })

    return {
        'annotation': {
            'cadd_phred': annotation.get('cadd_phred'),
            'dann_score': annotation.get('dann_score'),
            'eigen_phred': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'freqs': {
                'AF': annotation.get('freqs', {}).get('AF'),
                'topmedAF': annotation.get('freqs', {}).get('topmed_AF'),
                'g1k': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'exac': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'gnomad_exomes': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax', annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'gnomad_genomes': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
            },
            'gerp_rs': annotation.get('GERP_RS'),
            'phastcons100vert': annotation.get('phastCons100way_vertebrate'),

            'mpc_score': annotation.get('mpc_score'),
            'metasvm': annotation.get('metasvm'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'popCounts': {
                'AC': annotation.get('pop_counts', {}).get('AC'),
                'AN': annotation.get('pop_counts', {}).get('AN'),
                'g1kAC': annotation.get('pop_counts', {}).get('g1kAC'),
                'g1kAN': annotation.get('pop_counts', {}).get('g1kAN'),
                'topmedAC': annotation.get('pop_counts', {}).get('topmed_AC'),
                'topmedAN': annotation.get('pop_counts', {}).get('topmed_AN'),
                'gnomadExomesAC': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'gnomadExomesAN': annotation.get('pop_counts', {}).get('gnomad_exomes_AN'),
                'gnomadGenomesAC': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'gnomadGenomesAN': annotation.get('pop_counts', {}).get('gnomad_genomes_AN'),
                'exacAC': annotation.get('pop_counts', {}).get('exac_v3_AC'),
                'exac_hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'exac_hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
                'exacAN': annotation.get('pop_counts', {}).get('exac_v3_AN'),
                'gnomad_exomes_hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'gnomad_exomes_hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
                'gnomad_genomes_hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'gnomad_genomes_hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
            'primate_ai_score': annotation.get('primate_ai_score'),
            'splice_ai_delta_score': annotation.get('splice_ai_delta_score'),
            'revel_score': annotation.get('revel_score'),
            'rsid': annotation.get('rsid'),
            'sift': annotation.get('sift'),
            'vepConsequence': annotation.get('vep_consequence'),
            'vepGroup': annotation.get('vep_group'),
        },
        'mainTranscript': main_transcript,
        'clinvar': {
            'clinsig': extras.get('clinvar_clinsig'),
            'variantId': extras.get('clinvar_variant_id'),
            'alleleId': extras.get('clinvar_allele_id'),
            'goldStars': extras.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class') if (user and user.is_staff) else None,
        },
        'genotypes': genotypes,
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'locusLists': [],
        'origAltAlleles': extras.get('orig_alt_alleles', []),
        'transcripts': transcripts,
    }


def variant_main_transcript(variant_json):
    annotation = variant_json.get('annotation') or {}
    main_transcript = annotation.get('main_transcript') or (
        annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get(
            'worst_vep_annotation_index') is not None and annotation['vep_annotation'] else {})
    return {
        'transcriptId': main_transcript.get('feature') or main_transcript.get('transcript_id'),
        'geneId': main_transcript.get('gene') or main_transcript.get('gene_id'),
        'symbol': main_transcript.get('gene_symbol') or main_transcript.get('symbol'),
        'lof': main_transcript.get('lof'),
        'lofFlags': main_transcript.get('lof_flags'),
        'lofFilter': main_transcript.get('lof_filter'),
        'hgvsc': main_transcript.get('hgvsc'),
        'hgvsp': main_transcript.get('hgvsp'),
        'aminoAcids': main_transcript.get('amino_acids'),
        'proteinPosition': main_transcript.get('protein_position'),
    }



