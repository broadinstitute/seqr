import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_IN_REVIEW,
} from 'shared/constants/caseReviewConstants'

import {
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
} from 'shared/constants/familyAndIndividualConstants'

export const SHOW_ALL = 'ALL'
export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED_FOR_CASE_REVIEW'
export const SHOW_ANALYSIS_IN_PROGRESS = 'SHOW_ANALYSIS_IN_PROGRESS'
export const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'

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
  */
  {
    value: SHOW_ANALYSIS_IN_PROGRESS,
    name: 'Analysis In Progress',
    createFilter: familiesByGuid => familyGuid =>
    familiesByGuid[familyGuid].analysisStatus === FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
  },
  {
    value: SHOW_IN_REVIEW,
    name: 'In Review',
    createFilter: (familiesByGuid, individualsByGuid) => familyGuid =>
      familiesByGuid[familyGuid].individualGuids.filter(
        individualGuid => individualsByGuid[individualGuid].caseReviewStatus === CASE_REVIEW_STATUS_IN_REVIEW,
      ).length > 0,
  },
  {
    value: SHOW_MORE_INFO_NEEDED,
    name: 'Info Requested',
    createFilter: (familiesByGuid, individualsByGuid) => familyGuid =>
      familiesByGuid[familyGuid].individualGuids.filter(
        individualGuid => individualsByGuid[individualGuid].caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
      ).length > 0,
  },
]


export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
export const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'

export const FAMILY_SORT_OPTIONS = [
  {
    value: SORT_BY_FAMILY_NAME,
    name: 'Family Name',
    createSortKeyGetter: familiesByGuid => familyGuid => familiesByGuid[familyGuid].displayName,
  },
  {
    value: SORT_BY_FAMILY_ADDED_DATE,
    name: 'Family Added Date',
    createSortKeyGetter: familiesByGuid => familyGuid => familiesByGuid[familyGuid].createdDate || '2000-01-01T01:00:00.000Z',
  },
  {
    value: SORT_BY_DATA_LOADED_DATE,
    name: 'Data Loaded Date',
    createSortKeyGetter: (familiesByGuid, individualsByGuid, samplesByGuid) => familyGuid =>
      familiesByGuid[familyGuid].individualGuids.reduce(
        (acc, individualGuid) => {
          const indivLoadedDate = individualsByGuid[individualGuid].sampleGuids.reduce(
            (acc2, sampleGuid) => {
              const sampleLoadedDate = samplesByGuid[sampleGuid].loadedDate
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
