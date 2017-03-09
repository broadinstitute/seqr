/* eslint-disable no-multi-spaces */

//possible values
export const SHOW_ALL = 'SHOW_ALL'
export const SHOW_NEW = 'SHOW_NEW'

export const SORT_BY_PROJECT_NAME = 'SORT_BY_PROJECT_NAME'
export const SORT_BY_PROJECT_SAMPLES = 'SORT_BY_PROJECT_SAMPLES'
export const SORT_BY_NUM_FAMILIES = 'SORT_BY_NUM_FAMILIES'
export const SORT_BY_NUM_INDIVIDUALS = 'SORT_BY_NUM_INDIVIDUALS'
export const SORT_BY_DATE_CREATED = 'SORT_BY_DATE_CREATED'
export const SORT_BY_DATE_LAST_ACCESSED = 'SORT_BY_DATE_LAST_ACCESSED'
export const SORT_BY_TAGS = 'SORT_BY_TAGS'
export const SORT_BY_ANALYSIS = 'SORT_BY_ANALYSIS'

//export const SORT_BY_DATE_ACCESSED = 'SORT_BY_DATE_ACCESSED'

// modal
export const EDIT_NAME_MODAL = 'EDIT_NAME'
export const EDIT_DESCRIPTION_MODAL = 'EDIT_DESCRIPTION'
export const EDIT_CATEGORY_MODAL = 'EDIT_CATEGORY'
export const ADD_PROJECT_MODAL = 'ADD_PROJECT'
export const DELETE_PROJECT_MODAL = 'DELETE_PROJECT'

export const MODAL_SAVING = 'MODAL_SAVING'
export const MODAL_SAVE_SUCCEEDED = 'MODAL_SAVE_SUCCEEDED'
export const MODAL_SAVE_ERROR = 'MODAL_SAVE_ERROR'


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
  { key: 'Q',         color: '#AAAAAF', name: 'Waiting for data' },  //#FFC107
]
