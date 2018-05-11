/* eslint-disable no-multi-spaces */

import {
  FAMILY_STATUS_SOLVED,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_SOLVED_NOVEL_GENE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE,
  FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES,
  FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
} from 'shared/utils/constants'

export const ANALYSIS_TYPE_VARIANT_CALLS = 'VARIANTS'

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

export const CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS = [
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_STORE_DNA,   name: 'Store DNA' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_ARRAY,       name: 'Array' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_EXOME,       name: 'WES' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_GENOME,      name: 'WGS' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_RNASEQ,      name: 'RNA' },
  { value: CASE_REVIEW_STATUS_ACCEPTED_FOR_REPROCESSING,      name: 'Reprocess' },
]

export const SHOW_ALL = 'ALL'

export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_ACCEPTED = 'ACCEPTED'
export const SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
export const SHOW_UNCERTAIN = 'UNCERTAIN'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

export const SHOW_SOLVED = 'SHOW_SOLVED'
export const SHOW_STRONG_CANDIDATE = 'SHOW_STRONG_CANDIDATE'
export const SHOW_REVIEWED_NO_CLEAR_CANDIDATE = 'SHOW_REVIEWED_NO_CLEAR_CANDIDATE'
export const SHOW_ANALYSIS_IN_PROGRESS = 'SHOW_ANALYSIS_IN_PROGRESS'

export const SHOW_NOT_IN_REVIEW = 'NOT_IN_REVIEW'
export const SHOW_PENDING_RESULTS_AND_RECORDS = 'PENDING_RESULTS_AND_RECORDS'
export const SHOW_WAITLIST = 'WAITLIST'
export const SHOW_WITHDREW = 'WITHDREW'
export const SHOW_INELIGIBLE = 'INELIGIBLE'
export const SHOW_DECLINED_TO_PARTICIPATE = 'DECLINED_TO_PARTICIPATE'

export const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'


const SOLVED_STATUSES = new Set([
  FAMILY_STATUS_SOLVED,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_SOLVED_NOVEL_GENE,
])

const STRONG_CANDIDATE_STATUSES = new Set([
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE,
])

const ANALYSIS_IN_PROGRESS_STATUSES = new Set([
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
  FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES,
])


export const FAMILY_FILTER_OPTIONS = [
  {
    value: SHOW_ALL,
    name: 'All',
    createFilter: () => () => (true),
  },
  /*
  {
    value: SHOW_DATA_LOADED,
    name: 'Data Loaded',
    createFilter: (familiesByGuid, individualsByGuid, samplesByGuid) => familyGuid =>
      familiesByGuid[familyGuid].individualGuids.filter(
        individualGuid => individualsByGuid[individualGuid].sampleGuids.filter(
          sampleGuid => samplesByGuid[sampleGuid].isLoaded,
        ).length > 0,
      ).length > 0,
  },
   CASE_REVIEW_STATUS_ACCEPTED
  */
  {
    value: SHOW_SOLVED,
    name: 'Solved',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      SOLVED_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_STRONG_CANDIDATE,
    name: 'Strong Candidate',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      STRONG_CANDIDATE_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_REVIEWED_NO_CLEAR_CANDIDATE,
    name: 'No Clear Candidate',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family => family.analysisStatus === FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  },
  {
    value: SHOW_ANALYSIS_IN_PROGRESS,
    name: 'Analysis In Progress',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      ANALYSIS_IN_PROGRESS_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_ACCEPTED,
    name: 'Accepted',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED).length > 0,
  },
  {
    value: SHOW_NOT_ACCEPTED,
    name: 'Not Accepted',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_NOT_ACCEPTED).length > 0,
  },
  {
    value: SHOW_IN_REVIEW,
    name: 'In Review',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_IN_REVIEW).length > 0,
  },
  {
    value: SHOW_UNCERTAIN,
    name: 'Uncertain',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_UNCERTAIN).length > 0,
  },
  {
    value: SHOW_MORE_INFO_NEEDED,
    name: 'More Info Needed',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED).length > 0,
  },
  {
    value: SHOW_NOT_IN_REVIEW,
    name: 'Not In Review',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_NOT_IN_REVIEW).length > 0,
  },
  {
    value: SHOW_PENDING_RESULTS_AND_RECORDS,
    name: 'Pending Results and Records',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS).length > 0,
  },
  {
    value: SHOW_WAITLIST,
    name: 'Waitlist',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_WAITLIST).length > 0,
  },
  {
    value: SHOW_WITHDREW,
    name: 'Withdrew',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_WITHDREW).length > 0,
  },
  {
    value: SHOW_INELIGIBLE,
    name: 'Ineligible',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_INELIGIBLE).length > 0,
  },
  {
    value: SHOW_DECLINED_TO_PARTICIPATE,
    name: 'Declined to Participate',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE).length > 0,
  },
]


export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
export const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'

export const FAMILY_SORT_OPTIONS = [
  {
    value: SORT_BY_FAMILY_NAME,
    name: 'Family Name',
    /* eslint-disable no-unused-vars */
    createSortKeyGetter: families => family => family.displayName,
  },
  {
    value: SORT_BY_FAMILY_ADDED_DATE,
    name: 'Date Added',
    createSortKeyGetter: (families, individuals) => family =>
      individuals.filter(ind => ind.familyGuid === family.familyGuid).reduce(
        (acc, individual) => {
          const indivCreatedDate = individual.createdDate || '2000-01-01T01:00:00.000Z'
          return indivCreatedDate > acc ? indivCreatedDate : acc
        },
        '2000-01-01T01:00:00.000Z',
      ),
  },
  {
    value: SORT_BY_DATA_LOADED_DATE,
    name: 'Date Loaded',
    createSortKeyGetter: (families, individuals, samples) => family =>
      individuals.filter(ind => ind.familyGuid === family.familyGuid).reduce(
        (acc, individual) => {
          const indivLoadedDate = samples.filter(s => s.individualGuid === individual.individualGuid).reduce(
            (acc2, sample) => {
              const sampleLoadedDate = sample.loadedDate
              return sampleLoadedDate > acc2 ? sampleLoadedDate : acc2
            },
            '2000-01-01T01:00:00.000Z',
          )
          return indivLoadedDate > acc ? indivLoadedDate : acc
        },
        '2000-01-01T01:00:00.000Z',
      ),
  },
]
