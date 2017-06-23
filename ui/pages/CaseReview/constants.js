/* eslint-disable no-multi-spaces */
import {
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_IN_REVIEW,
  CASE_REVIEW_STATUS_UNCERTAIN,
  CASE_REVIEW_STATUS_NOT_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_NOT_IN_REVIEW,
  CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS,
  CASE_REVIEW_STATUS_WAITLIST,

  CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_REPROCESSING,
} from '../../shared/constants/caseReviewConstants'

export const SHOW_ALL = 'ALL'
export const SHOW_ACCEPTED = 'ACCEPTED'
export const SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_UNCERTAIN = 'UNCERTAIN'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'
export const SHOW_NOT_IN_REVIEW = 'NOT_IN_REVIEW'
export const SHOW_PENDING_RESULTS_AND_RECORDS = 'PENDING_RESULTS_AND_RECORDS'
export const SHOW_WAITLIST = 'WAITLIST'

export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_DATE_ADDED = 'DATE_ADDED'
export const SORT_BY_DATE_LAST_CHANGED = 'DATE_LAST_CHANGED'

export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW,                   name: 'In Review',             color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN,                   name: 'Uncertain',             color: '#fddb28' },
  { value: CASE_REVIEW_STATUS_ACCEPTED,                    name: 'Accepted',              color: '#8BC34A' },
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#4f5cb3' },  //#C5CAE9
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: '#F44336' },  //#673AB7
  { value: CASE_REVIEW_STATUS_NOT_IN_REVIEW,               name: 'Not In Review',         color: '#AAAAAA' },
  { value: CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS, name: 'Pending Results and Records', color: '#996699' },
  { value: CASE_REVIEW_STATUS_WAITLIST,                    name: 'Waitlist',              color: '#990099' },
]

export const CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS = [
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA,   name: 'Store DNA' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY,       name: 'Array' },
  '---', /* adds line break */
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME,       name: 'WES' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME,      name: 'WGS' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ,      name: 'RNA' },
  '---',
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_REPROCESSING,      name: 'Reprocess' },
]


export const CASE_REVIEW_STATUS_OPT_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)
