import orderBy from 'lodash/orderBy'
import { createSelector } from 'reselect'

import {
  getProjectFamilies,
  getProjectIndividuals,
  getProjectSamples,
} from 'redux/rootReducer'

import { CASE_REVIEW_STATUS_OPTIONS } from 'shared/constants/caseReviewConstants'
import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/constants/familyAndIndividualConstants'

import {
  getFamiliesFilter,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  getProjectTablePage,
  getProjectTableRecordsPerPage,
} from '../reducers'

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
export const getFilteredFamilies = createSelector(
  getProjectFamilies,
  getProjectIndividuals,
  getFamiliesFilter,
  (families, individuals, familiesFilter) => {
    if (!familiesFilter || !FAMILY_FILTER_LOOKUP[familiesFilter]) {
      return families
    }

    const familyFilter = FAMILY_FILTER_LOOKUP[familiesFilter](families, individuals)
    return families.filter(familyFilter)
  },
)

/**
 * function that returns the total number of pages to show.
 *
 * @param state {object} global Redux state
 */
export const getTotalPageCount = createSelector(
  getFilteredFamilies,
  getProjectTableRecordsPerPage,
  (filteredFamilies, recordsPerPage) => {
    return Math.max(1, Math.ceil(filteredFamilies.length / recordsPerPage))
  },
)

/**
 * function that returns an array of currently-visible familyGuids based on the selected page.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilies = createSelector(
  getFilteredFamilies,
  getProjectTablePage,
  getProjectTableRecordsPerPage,
  getTotalPageCount,
  (filteredFamilies, currentPage, recordsPerPage, totalPageCount) => {
    const page = Math.min(currentPage, totalPageCount) - 1
    return filteredFamilies.slice(page * recordsPerPage, (page + 1) * recordsPerPage)
  },
)


/**
 * function that returns an array of currently-visible family objects, sorted according to
 * currently-selected values of familiesSortOrder and familiesSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamiliesInSortedOrder = createSelector(
  getVisibleFamilies,
  getProjectFamilies,
  getProjectIndividuals,
  getProjectSamples,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilies, families, individuals, samples, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder]) {
      return visibleFamilies
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](families, individuals, samples)

    return orderBy(visibleFamilies, [getSortKey], [familiesSortDirection > 0 ? 'asc' : 'desc'])
  },
)

/**
 * function that returns a mapping of each familyGuid to an array of individuals in that family.
 * The array of individuals is in sorted order.
 *
 * @param state {object} global Redux state
 */
export const getVisibleSortedFamiliesWithIndividuals = createSelector(
  getVisibleFamiliesInSortedOrder,
  getProjectIndividuals,
  (visibleFamilies, individuals) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivSortKey = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0

    return visibleFamilies.map((family) => {
      const familyIndividuals = orderBy(individuals.filter(ind => ind.familyGuid === family.familyGuid), [getIndivSortKey])
      return Object.assign(family, { individuals: familyIndividuals })
    })
  },
)

export const getCaseReviewStatusCounts = createSelector(
  getProjectIndividuals,
  (individuals) => {
    const caseReviewStatusCounts = individuals.reduce((acc, individual) => ({
      ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1,
    }), {})

    return CASE_REVIEW_STATUS_OPTIONS.map(option => (
      { ...option, count: (caseReviewStatusCounts[option.value] || 0) }),
    )
  })

export const getAnalysisStatusCounts = createSelector(
  getProjectFamilies,
  (families) => {
    const analysisStatusCounts = families.reduce((acc, family) => ({
      ...acc, [family.analysisStatus]: (acc[family.analysisStatus] || 0) + 1,
    }), {})

    return FAMILY_ANALYSIS_STATUS_OPTIONS.map(option => (
      { ...option, count: (analysisStatusCounts[option.key] || 0) }),
    )
  })
