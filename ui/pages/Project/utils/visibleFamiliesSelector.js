import orderBy from 'lodash/orderBy'
import { createSelector } from 'reselect'

import {
  getFamiliesByGuid,
  getIndividualsByGuid,
  getSamplesByGuid,
} from 'shared/utils/redux/commonDataActionsAndSelectors'

import {
  getFamiliesFilter,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  getProjectTablePage,
  getProjectTableRecordsPerPage,
} from '../redux/rootReducer'

import {
  FAMILY_FILTER_OPTIONS,
  FAMILY_SORT_OPTIONS,
} from '../constants'


const FAMILY_FILTER_LOOKUP = FAMILY_FILTER_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.createFilter },
  }), {},
)

const FAMILY_SORT_LOOKUP = FAMILY_SORT_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.createSortKeyGetter },
  }), {},
)

/**
 * function that returns an array of family guids that pass the currently-selected
 * familiesFilter.
 *
 * @param state {object} global Redux state
 */
export const getFilteredFamilyGuids = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getFamiliesFilter,
  (familiesByGuid, individualsByGuid, familiesFilter) => {
    if (!familiesFilter || !FAMILY_FILTER_LOOKUP[familiesFilter]) {
      return Object.keys(familiesByGuid)
    }

    const familyFilter = FAMILY_FILTER_LOOKUP[familiesFilter](familiesByGuid, individualsByGuid)
    const filteredFamilyGuids = Object.keys(familiesByGuid).filter(familyFilter)
    return filteredFamilyGuids
  },
)

/**
 * function that returns the total number of pages to show.
 *
 * @param state {object} global Redux state
 */
export const getTotalPageCount = createSelector(
  getFilteredFamilyGuids,
  getProjectTableRecordsPerPage,
  (filteredFamiliesByGuid, recordsPerPage) => {
    return Math.max(1, Math.ceil(Object.keys(filteredFamiliesByGuid).length / recordsPerPage))
  },
)

/**
 * function that returns an array of currently-visible familyGuids based on the selected page.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilyGuids = createSelector(
  getFilteredFamilyGuids,
  getProjectTablePage,
  getProjectTableRecordsPerPage,
  getTotalPageCount,
  (filteredFamiliesByGuid, currentPage, recordsPerPage, totalPageCount) => {
    const page = Math.min(currentPage, totalPageCount) - 1
    return filteredFamiliesByGuid.slice(page * recordsPerPage, (page + 1) * recordsPerPage)
  },
)


/**
 * function that returns an array of currently-visible family objects, sorted according to
 * currently-selected values of familiesSortOrder and familiesSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamiliesInSortedOrder = createSelector(
  getVisibleFamilyGuids,
  getFamiliesByGuid,
  getIndividualsByGuid,
  getSamplesByGuid,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilyGuids, familiesByGuid, individualsByGuid, samplesByGuid, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder]) {
      return visibleFamilyGuids
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](familiesByGuid, individualsByGuid, samplesByGuid)

    const sortedFamilyGuids = orderBy(visibleFamilyGuids, [getSortKey], [familiesSortDirection > 0 ? 'asc' : 'desc'])
    const sortedFamilies = sortedFamilyGuids.map(familyGuid => familiesByGuid[familyGuid])
    return sortedFamilies
  },
)

/**
 * function that returns a mapping of each familyGuid to an array of individuals in that family.
 * The array of individuals is in sorted order.
 *
 * @param state {object} global Redux state
 */
export const getFamilyGuidToIndividuals = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  (familiesByGuid, individualsByGuid) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivGuidSortKey = individualGuid => AFFECTED_STATUS_ORDER[individualsByGuid[individualGuid].affected] || 0

    const familyGuidToIndividuals = Object.keys(familiesByGuid).reduce((acc, familyGuid) => ({
      ...acc,
      [familyGuid]: orderBy(familiesByGuid[familyGuid].individualGuids, [getIndivGuidSortKey]).map(
        individualGuid => individualsByGuid[individualGuid],
      ),
    }), {})

    return familyGuidToIndividuals
  },
)
