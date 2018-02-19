/* eslint-disable no-multi-spaces */

export const CASE_REVIEW_STATUS_NOT_IN_REVIEW = 'N'
export const CASE_REVIEW_STATUS_IN_REVIEW = 'I'
export const CASE_REVIEW_STATUS_UNCERTAIN = 'U'
export const CASE_REVIEW_STATUS_ACCEPTED = 'A'
export const CASE_REVIEW_STATUS_NOT_ACCEPTED = 'R'
export const CASE_REVIEW_STATUS_MORE_INFO_NEEDED = 'Q'
export const CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS = 'P'
export const CASE_REVIEW_STATUS_WAITLIST = 'W'
export const CASE_REVIEW_STATUS_WITHDREW = 'WD'
export const CASE_REVIEW_STATUS_INELIGIBLE = 'IE'
export const CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE = 'DP'

export const CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA = 'S'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY = 'A'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME = 'E'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME = 'G'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ = 'R'
export const CASE_REVIEW_STATUS_ACCEPTED_FOR_REPROCESSING = 'P'


export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW,                   name: 'In Review',             color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN,                   name: 'Uncertain',             color: '#fddb28' },
  { value: CASE_REVIEW_STATUS_ACCEPTED,                    name: 'Accepted',              color: '#8BC34A' },
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#4f5cb3' },  //#C5CAE9
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: '#F44336' },  //#673AB7
  { value: CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS, name: 'Pending Results and Records', color: '#996699' },
  { value: CASE_REVIEW_STATUS_NOT_IN_REVIEW,               name: 'Not In Review',         color: '#118833' },
  { value: CASE_REVIEW_STATUS_WAITLIST,                    name: 'Waitlist',              color: '#990099' },
  { value: CASE_REVIEW_STATUS_WITHDREW,                    name: 'Withdrew',              color: '#999999' },
  { value: CASE_REVIEW_STATUS_INELIGIBLE,                  name: 'Ineligible',            color: '#111111' },
  { value: CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE,     name: 'Declined To Participate', color: '#FF8800' },
]

export const CASE_REVIEW_STATUS_OPT_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)
