/* eslint-disable no-multi-spaces */

export const FAMILY_STATUS_ANALYSIS_IN_PROGRESS = 'I'

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
