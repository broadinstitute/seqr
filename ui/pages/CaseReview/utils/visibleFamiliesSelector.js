/* eslint-disable */
import { createSelector } from 'reselect'

import { createFamilyFilter } from './familyAndIndividualFilter'
import { createFamilySortComparator, createIndividualSortComparator } from './familyAndIndividualSort'

import {
  getFamiliesByGuid,
  getIndividualsByGuid,
  getFamilyGuidToIndivGuids,
  getFamiliesFilter,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
} from '../reducers/rootReducer'

/**
 * function that returns an array of currently-visible familyGuids based on the currently-selected
 * value of familiesFilter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilyGuids = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getFamilyGuidToIndivGuids,
  getFamiliesFilter,
  (familiesByGuid, individualsByGuid, familyGuidToIndivGuids, familiesFilter) => {
    const familyFilter = createFamilyFilter(familiesFilter, familyGuidToIndivGuids, individualsByGuid)
    const visibleFamilyGuids = Object.keys(familiesByGuid).filter(familyFilter)
    return visibleFamilyGuids
  },
)

/**
 * function that returns an array of currently-visible familyGuids (like getVisibleFamilyGuids),
 * but sorts it according to currently-selected values of familiesSortOrder and familiesSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamiliesInSortedOrder = createSelector(
  getVisibleFamilyGuids,
  getFamiliesByGuid,
  getIndividualsByGuid,
  getFamilyGuidToIndivGuids,

  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilyGuids, familiesByGuid, individualsByGuid, familyGuidToIndivGuids, familiesSortOrder, familiesSortDirection) => {
    const familyGuidComparator = createFamilySortComparator(
      familiesSortOrder, familiesSortDirection, familiesByGuid, familyGuidToIndivGuids, individualsByGuid)

    const visibleFamilyGuidsCopy = [...visibleFamilyGuids]
    const sortedFamilyGuids = visibleFamilyGuidsCopy.sort(familyGuidComparator)
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
  getFamilyGuidToIndivGuids,
  (familiesByGuid, individualsByGuid, familyGuidToIndivGuids) => {
    const individualsComparator = createIndividualSortComparator(individualsByGuid)
    const familyGuidToIndividuals = Object.keys(familiesByGuid).reduce((acc, familyGuid) => {
      const individualGuidsCopy = [...familyGuidToIndivGuids[familyGuid]]
      return {
        ...acc,
        [familyGuid]: individualGuidsCopy.sort(individualsComparator).map(individualGuid => individualsByGuid[individualGuid]),
      }
    }, {})

    return familyGuidToIndividuals
  },
)
