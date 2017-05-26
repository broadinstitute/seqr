/* eslint-disable no-multi-spaces */

export const SHOW_ALL = 'ALL'
export const SHOW_ACCEPTED = 'ACCEPTED'
export const SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_UNCERTAIN = 'UNCERTAIN'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_DATE_ADDED = 'DATE_ADDED'
export const SORT_BY_DATE_LAST_CHANGED = 'DATE_LAST_CHANGED'

export const CASE_REVIEW_STATUS_IN_REVIEW = 'I'
export const CASE_REVIEW_STATUS_UNCERTAIN = 'U'
export const CASE_REVIEW_STATUS_ACCEPTED = 'A'
export const CASE_REVIEW_STATUS_NOT_ACCEPTED = 'R'
export const CASE_REVIEW_STATUS_MORE_INFO_NEEDED = 'Q'

export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW,                   name: 'In Review',             color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN,                   name: 'Uncertain',             color: '#FDDD1A' },
  { value: CASE_REVIEW_STATUS_ACCEPTED,                    name: 'Accepted',              color: '#8BC34A' },  //#673AB7
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#F44336' },  //C5CAE9
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: 'purple'   },
]

export const CASE_REVIEW_STATUS_NAME_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({ ...acc,  ...{ [opt.value]: opt.text } }),
  {},
)

export const CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA = 'S'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY = 'A'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME = 'E'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME = 'G'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ = 'R'


export const CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS = [
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA,   name: 'Store DNA' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY,       name: 'Array' },
  '---', /* adds line break */
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME,       name: 'WES' },  //#673AB7
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME,      name: 'WGS' },  //C5CAE9
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ,      name: 'RNA' },
]
