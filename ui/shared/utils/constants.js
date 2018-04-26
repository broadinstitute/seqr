/* eslint-disable no-multi-spaces */

// ANALYSIS STATUS

export const FAMILY_STATUS_SOLVED = 'S'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE = 'S_kgfp'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'S_kgdp'
export const FAMILY_STATUS_SOLVED_NOVEL_GENE = 'S_ng'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE = 'Sc_kgfp'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'Sc_kgdp'
export const FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE = 'Sc_ng'
export const FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES = 'Rcpc'
export const FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE = 'Rncc'
export const FAMILY_STATUS_ANALYSIS_IN_PROGRESS = 'I'
//export const FAMILY_STATUS_WAITING_FOR_DATA = 'Q'

export const FAMILY_ANALYSIS_STATUS_OPTIONS = [
  { key: 'S',         color: '#4CAF50', name: 'Solved' },
  { key: 'S_kgfp',    color: '#4CAF50', name: 'Solved - known gene for phenotype' },
  { key: 'S_kgdp',    color: '#4CAF50', name: 'Solved - gene linked to different phenotype' },
  { key: 'S_ng',      color: '#4CAF50', name: 'Solved - novel gene' },
  { key: 'Sc_kgfp',   color: '#CDDC39', name: 'Strong candidate - known gene for phenotype' },
  { key: 'Sc_kgdp',   color: '#CDDC39', name: 'Strong candidate - gene linked to different phenotype' },
  { key: 'Sc_ng',     color: '#CDDC39', name: 'Strong candidate - novel gene' },
  { key: 'Rcpc',      color: '#CDDC39', name: 'Reviewed, currently pursuing candidates' },
  { key: 'Rncc',      color: '#EF5350', name: 'Reviewed, no clear candidate' },
  { key: 'I',         color: '#4682B4', name: 'Analysis in Progress' },
  { key: 'Q',         color: '#FFC107', name: 'Waiting for data' },  //#FFC107, #AAAAAF
]

export const FAMILY_ANALYSIS_STATUS_LOOKUP = FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.key]: opt },
  }), {},
)

// CLINVAR

export const CLINSIG_SEVERITY = {
  pathogenic: 1,
  'risk factor': 0,
  'likely pathogenic': 1,
  benign: -1,
  'likely benign': -1,
  protective: -1,
}
