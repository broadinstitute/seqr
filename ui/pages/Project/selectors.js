import orderBy from 'lodash/orderBy'
import { createSelector } from 'reselect'

import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/utils/constants'

import {
  getProjectsByGuid, getFamiliesByGuid, getIndividualsByGuid, getSamplesByGuid, getDatasetsByGuid,
} from 'redux/selectors'

import {
  SHOW_ALL,
  SORT_BY_FAMILY_NAME,
  CASE_REVIEW_STATUS_OPTIONS,
  FAMILY_FILTER_OPTIONS,
  FAMILY_SORT_OPTIONS,
  SORT_BY_FAMILY_GUID,
  VARIANT_SORT_OPTONS,
} from './constants'


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

const VARIANT_SORT_LOOKUP = VARIANT_SORT_OPTONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.comparator },
  }), {},
)

// project data selectors

export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
export const getProjectSavedVariantsIsLoading = state => state.projectSavedVariantsLoading.isLoading
export const getProjectGuid = state => state.currentProjectGuid

export const getProject = createSelector(
  getProjectsByGuid, getProjectGuid, (projectsByGuid, currentProjectGuid) => projectsByGuid[currentProjectGuid],
)

const filterProjectEntities = (entities, currentProjectGuid) =>
  Object.values(entities).filter(o => o.projectGuid === currentProjectGuid)

export const getProjectFamilies = createSelector(getFamiliesByGuid, getProjectGuid, filterProjectEntities)

export const getProjectIndividuals = createSelector(getIndividualsByGuid, getProjectGuid, filterProjectEntities)

export const getProjectDatasets = createSelector(getDatasetsByGuid, getProjectGuid, filterProjectEntities)

export const getProjectSamples = createSelector(getSamplesByGuid, getProjectGuid, filterProjectEntities)

// Saved variant selectors

export const getSavedVariantTableState = state => state.savedVariantTableState
export const getSavedVariantCategoryFilter = (state, props) => { return props.match.params.tag ? SHOW_ALL : (state.savedVariantTableState.categoryFilter || SHOW_ALL) }
export const getSavedVariantSortOrder = state => state.savedVariantTableState.sortOrder || SORT_BY_FAMILY_GUID
export const getSavedVariantHideExcluded = state => state.savedVariantTableState.hideExcluded

export const getProjectSavedVariants = createSelector(
  state => state.projectSavedVariants,
  (state, props) => props.match.params,
  (projectSavedVariants, { tag, familyGuid }) => {
    const variants = familyGuid ? projectSavedVariants[familyGuid] || [] : Object.values(projectSavedVariants).reduce((a, b) => a.concat(b), [])
    return tag ? variants.filter(o => o.tags.some(t => t.name === tag)) : variants
  },
)

export const getVisibleSortedProjectSavedVariants = createSelector(
  getProjectSavedVariants, getSavedVariantCategoryFilter, getSavedVariantSortOrder, getSavedVariantHideExcluded,
  (projectSavedVariants, categoryFilter, sortOrder, hideExcluded) => {
    let variantsToShow = projectSavedVariants
    if (hideExcluded) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.every(t => t.name !== 'Excluded'))
    }
    if (categoryFilter !== SHOW_ALL) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.some(t => t.category === categoryFilter))
    }
    // Always secondary sort on xpos
    variantsToShow.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sortOrder](a, b) || a.xpos - b.xpos
    })
    return variantsToShow
  },
)

// Family table selectors
export const getProjectTableState = state => state.familyTableState
export const getProjectTablePage = state => state.familyTableState.currentPage || 1
export const getProjectTableRecordsPerPage = state => state.familyTableState.recordsPerPage || 200
export const getFamiliesFilter = state => state.familyTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.familyTableState.familiesSortDirection || 1
export const getShowDetails = state => (state.familyTableState.showDetails !== undefined ? state.familyTableState.showDetails : true)

export const getProjectIndividualsWithFamily = createSelector(
  getProjectIndividuals,
  getFamiliesByGuid,
  (projectIndividuals, familiesByGuid) =>
    projectIndividuals.map((ind) => { return { family: familiesByGuid[ind.familyGuid], ...ind } }),
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
      { ...option, count: (analysisStatusCounts[option.value] || 0) }),
    )
  })
