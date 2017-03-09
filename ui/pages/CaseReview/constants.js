/* eslint-disable no-multi-spaces */

export const SHOW_ALL = 'ALL'
export const SHOW_ACCEPTED = 'ACCEPTED'
export const SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_UNCERTAIN = 'UNCERTAIN'
export const SHOW_HOLD = 'HOLD'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_DATE_ADDED = 'DATE_ADDED'
export const SORT_BY_DATE_LAST_CHANGED = 'DATE_LAST_CHANGED'

export const CASE_REVIEW_STATUS_IN_REVIEW_KEY = 'I'
export const CASE_REVIEW_STATUS_UNCERTAIN_KEY = 'U'
export const CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY = 'A'
export const CASE_REVIEW_STATUS_ACCEPTED_EXOME = 'E'
export const CASE_REVIEW_STATUS_ACCEPTED_GENOME = 'G'
export const CASE_REVIEW_STATUS_ACCEPTED_RNASEQ = '3'
export const CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY = 'R'
export const CASE_REVIEW_STATUS_HOLD_KEY = 'H'
export const CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY = 'Q'

export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW_KEY,                   name: 'In Review',         color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN_KEY,                   name: 'Uncertain',         color: '#8BC34A' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY, name: 'Accepted: Platform Uncertain', color: '#F44336' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_EXOME,                  name: 'Accepted: Exome',   color: '#673AB7' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_GENOME,                 name: 'Accepted: Genome',  color: '#FFC107' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_RNASEQ,                 name: 'Accepted: RNA-seq', color: '#880E4F' },
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY,                name: 'Not Accepted',      color: '#C5CAE9' },
  { value: CASE_REVIEW_STATUS_HOLD_KEY,                        name: 'Hold',              color: 'brown'   },
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY,            name: 'More Info Needed',  color: 'black'   },
]

export const CASE_REVIEW_STATUS_NAME_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({ ...acc,  ...{ [opt.value]: opt.text } }),
  {},
)
