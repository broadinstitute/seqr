export const THIS_CALLSET_FREQUENCY = 'callset'
export const SV_CALLSET_FREQUENCY = 'sv_callset'
export const TOPMED_FREQUENCY = 'topmed'
export const SNP_FREQUENCIES = [
  {
    name: 'gnomad_genomes',
    label: 'gnomAD genomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or by allele frequency (popmax AF) in any one of these five subpopulations defined for gnomAD genomes: AFR, AMR, EAS, NFE, SAS',
  },
  {
    name: 'gnomad_exomes',
    label: 'gnomAD exomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD exomes, or by allele frequency (popmax AF) in any one of these five subpopulations defined for gnomAD exomes: AFR, AMR, EAS, NFE, SAS',
  },
  {
    name: TOPMED_FREQUENCY,
    label: 'TOPMed',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) or allele frequency (AF) in TOPMed',
  },
  {
    name: THIS_CALLSET_FREQUENCY,
    label: 'This Callset',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or by allele frequency (AF) among the samples in this family plus the rest of the samples that were joint-called as part of variant calling for this project.',
  },
]

export const MITO_FREQUENCIES = [
  {
    name: 'gnomad_mito',
    label: 'gnomAD homoplasmic',
    homHemi: false,
    labelHelp: 'Filter by the gnomAD allele count (AC) and allele frequency (AF) restricted to variants with a heteroplasmy level >= 0.95',
  },
]

export const SV_CALLSET_CRITERIA_MESSAGE = 'Only an SV that is estimated to be the same SV (type and breakpoints) among jointly genotyped samples will be counted as an allele. CNVs called on exomes have unknown breakpoints so similar overlapping CNVs may be counted as an allele.'
export const GNOMAD_SV_CRITERIA_MESSAGE = 'The following criteria need to be met for an SV in gnomAD to be counted as an allele: Has the same SV type (deletion, duplication, etc) and either has sufficient reciprocal overlap (SVs >5Kb need 50%, SVs < 5Kb need 10%) or has insertion breakpoints within 100bp'
export const SV_FREQUENCIES = [
  {
    name: 'gnomad_svs',
    label: 'gnomAD genome SVs',
    homHemi: false,
    labelHelp: `Filter by locus frequency (AF) among gnomAD SVs. ${GNOMAD_SV_CRITERIA_MESSAGE}`,
  },
  {
    name: SV_CALLSET_FREQUENCY,
    label: 'This SV Callset',
    homHemi: false,
    labelHelp: `Filter by allele count (AC) or by allele frequency (AF) among all the jointly genotyped samples that were part of the Structural Variant (SV) calling for this project. ${SV_CALLSET_CRITERIA_MESSAGE}`,
  },
]

export const FREQUENCIES = [...SNP_FREQUENCIES, ...MITO_FREQUENCIES, ...SV_FREQUENCIES]
