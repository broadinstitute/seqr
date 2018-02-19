import { createSelector } from 'reselect'
import { getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'

import { createFamilyFilter } from './familyAndIndividualFilter'
import { createFamilySortComparator, createIndividualSortComparator } from './familyAndIndividualSort'

import {
  getFamiliesFilter,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  getCaseReviewTablePage,
  getCaseReviewTableRecordsPerPage,
} from '../redux/rootReducer'


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
    if (!familiesFilter) {
      return Object.keys(familiesByGuid)
    }

    const familyFilter = createFamilyFilter(familiesFilter, familiesByGuid, individualsByGuid)
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
  getCaseReviewTableRecordsPerPage,
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
  getCaseReviewTablePage,
  getCaseReviewTableRecordsPerPage,
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
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilyGuids, familiesByGuid, individualsByGuid, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder) {
      return visibleFamilyGuids
    }

    const familyGuidComparator = createFamilySortComparator(
      familiesSortOrder, familiesSortDirection, familiesByGuid, individualsByGuid)

    const sortedFamilyGuids = [...visibleFamilyGuids].sort(familyGuidComparator)
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
    const individualsComparator = createIndividualSortComparator(individualsByGuid)

    const familyGuidToIndividuals = Object.values(familiesByGuid).reduce((acc, family) => {
      const sortedIndividualGuids = [...family.individualGuids].sort(individualsComparator)
      return {
        ...acc,
        [family.familyGuid]: sortedIndividualGuids.map(individualGuid => individualsByGuid[individualGuid]),
      }
    }, {})

    return familyGuidToIndividuals
  },
)
