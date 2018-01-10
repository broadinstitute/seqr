import { createSelector } from 'reselect'
import { getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'

import { createFamilyFilter } from './familyAndIndividualFilter'
import { createFamilySortComparator, createIndividualSortComparator } from './familyAndIndividualSort'

import {
  getFamiliesFilter,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
} from '../redux/rootReducer'

/**
 * function that returns an array of currently-visible familyGuids based on the currently-selected
 * value of familiesFilter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilyGuids = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getFamiliesFilter,
  (familiesByGuid, individualsByGuid, familiesFilter) => {
    if (!familiesFilter) {
      return Object.keys(familiesByGuid)
    }

    const familyFilter = createFamilyFilter(familiesFilter, familiesByGuid, individualsByGuid)
    const visibleFamilyGuids = Object.keys(familiesByGuid).filter(familyFilter)
    return visibleFamilyGuids
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
