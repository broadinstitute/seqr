import orderBy from 'lodash/orderBy'
import { createSelector } from 'reselect'

import { getSearchResults } from 'redux/utils/reduxSearchEnhancer'
import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/utils/constants'

import {
  getProjectsByGuid, getFamiliesByGuid, getIndividualsByGuid, getSamplesByGuid, getUser,
} from 'redux/selectors'

import {
  SHOW_ALL,
  SORT_BY_FAMILY_NAME,
  CASE_REVIEW_STATUS_OPTIONS,
  FAMILY_FILTER_OPTIONS,
  FAMILY_SORT_OPTIONS,
  FAMILY_EXPORT_DATA,
  INDIVIDUAL_EXPORT_DATA,
  SORT_BY_FAMILY_GUID,
  VARIANT_SORT_OPTONS,
  VARIANT_EXPORT_DATA,
  VARIANT_GENOTYPE_EXPORT_DATA,
  familySamplesLoaded,
} from './constants'


const FAMILY_FILTER_LOOKUP = FAMILY_FILTER_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.createFilter,
  }), {},
)

const FAMILY_SORT_LOOKUP = FAMILY_SORT_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.createSortKeyGetter,
  }), {},
)

const VARIANT_SORT_LOOKUP = VARIANT_SORT_OPTONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.comparator,
  }), {},
)

// project data selectors

export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
export const getProjectSavedVariantsIsLoading = state => state.projectSavedVariantsLoading.isLoading
export const getProjectGuid = state => state.currentProjectGuid

export const getProject = createSelector(
  getProjectsByGuid, getProjectGuid, (projectsByGuid, currentProjectGuid) => projectsByGuid[currentProjectGuid],
)


const groupEntitiesByProjectGuid = entities => Object.entries(entities).reduce((acc, [entityGuid, entity]) => {
  if (!(entity.projectGuid in acc)) {
    acc[entity.projectGuid] = {}
  }
  acc[entity.projectGuid][entityGuid] = entity

  return acc

}, {})

export const getFamiliesGroupedByProjectGuid = createSelector(getFamiliesByGuid, groupEntitiesByProjectGuid)
export const getIndividualsGroupedByProjectGuid = createSelector(getIndividualsByGuid, groupEntitiesByProjectGuid)
export const getSamplesGroupedByProjectGuid = createSelector(getSamplesByGuid, groupEntitiesByProjectGuid)


const selectEntitiesForProjectGuid = (entitiesGroupedByProjectGuid, projectGuid) => entitiesGroupedByProjectGuid[projectGuid] || {}

export const getProjectFamiliesByGuid = createSelector(getFamiliesGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid)
export const getProjectIndividualsByGuid = createSelector(getIndividualsGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid)
export const getProjectSamplesByGuid = createSelector(getSamplesGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid)

// Saved variant selectors
export const getSavedVariantTableState = state => state.savedVariantTableState
export const getSavedVariantCategoryFilter = state => state.savedVariantTableState.categoryFilter || SHOW_ALL
export const getSavedVariantSortOrder = state => state.savedVariantTableState.sortOrder || SORT_BY_FAMILY_GUID
export const getSavedVariantHideExcluded = state => state.savedVariantTableState.hideExcluded
export const getSavedVariantCurrentPage = state => state.savedVariantTableState.currentPage || 1
export const getSavedVariantRecordsPerPage = state => state.savedVariantTableState.recordsPerPage || 25

export const getProjectSavedVariants = createSelector(
  state => state.projectSavedVariants,
  (state, props) => props.match.params,
  (projectSavedVariants, { tag, familyGuid, variantGuid }) => {
    let variants = Object.values(projectSavedVariants)
    if (variantGuid) {
      return variants.filter(o => o.variantId === variantGuid)
    }
    if (familyGuid) {
      variants = variants.filter(o => o.familyGuid === familyGuid)
    }
    return tag ? variants.filter(o => o.tags.some(t => t.name === tag)) : variants
  },
)

export const getSavedVariantVisibleIndices = createSelector(
  getSavedVariantCurrentPage, getSavedVariantRecordsPerPage,
  (currentPage, recordsPerPage) => {
    return [(currentPage - 1) * recordsPerPage, currentPage * recordsPerPage]
  },
)

export const getFilteredProjectSavedVariants = createSelector(
  getProjectSavedVariants,
  getSavedVariantCategoryFilter,
  getSavedVariantHideExcluded,
  (projectSavedVariants, categoryFilter, hideExcluded) => {
    let variantsToShow = projectSavedVariants
    if (hideExcluded) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.every(t => t.name !== 'Excluded'))
    }
    if (categoryFilter !== SHOW_ALL) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.some(t => t.category === categoryFilter))
    }
    return variantsToShow
  },
)

export const getVisibleSortedProjectSavedVariants = createSelector(
  getFilteredProjectSavedVariants,
  getSavedVariantSortOrder,
  getSavedVariantVisibleIndices,
  (filteredSavedVariants, sortOrder, visibleIndices) => {
    // Always secondary sort on xpos
    filteredSavedVariants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sortOrder](a, b) || a.xpos - b.xpos
    })
    return filteredSavedVariants.slice(...visibleIndices)
  },
)

export const getSavedVariantTotalPages = createSelector(
  getFilteredProjectSavedVariants, getSavedVariantRecordsPerPage,
  (filteredSavedVariants, recordsPerPage) => {
    return Math.max(1, Math.ceil(filteredSavedVariants.length / recordsPerPage))
  },
)

export const getSavedVariantExportConfig = createSelector(
  getFilteredProjectSavedVariants,
  (filteredSavedVariants) => {
    const maxGenotypes = Math.max(...filteredSavedVariants.map(variant => Object.keys(variant.genotypes).length), 0)
    return {
      rawData: filteredSavedVariants,
      headers: [...Array(maxGenotypes).keys()].reduce(
        (acc, i) => [...acc, ...VARIANT_GENOTYPE_EXPORT_DATA.map(config => `${config.header}_${i + 1}`)],
        VARIANT_EXPORT_DATA.map(config => config.header),
      ),
      processRow: variant => Object.keys(variant.genotypes).reduce(
        (acc, individualId) => [...acc, ...VARIANT_GENOTYPE_EXPORT_DATA.map((config) => {
          const genotype = variant.genotypes[individualId]
          return config.getVal ? config.getVal(genotype, individualId) : genotype[config.header]
        })],
        VARIANT_EXPORT_DATA.map(config => (config.getVal ? config.getVal(variant) : variant[config.header])),
      ),
    }
  },
)

// Family table selectors
export const getFamiliesTableState = state => state.familyTableState
export const getFamiliesFilter = state => state.familyTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.familyTableState.familiesSortDirection || 1

/**
 * function that returns an array of family guids that pass the currently-selected
 * familiesFilter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilies = createSelector(
  getProjectFamiliesByGuid,
  getProjectIndividualsByGuid,
  getProjectSamplesByGuid,
  getUser,
  getFamiliesFilter,
  getSearchResults('familiesByGuid'),
  (familiesByGuid, individualsByGuid, samplesByGuid, user, familiesFilter, familySearchResults) => {
    const searchedFamilies = familySearchResults.map(family => familiesByGuid[family]).filter(family => family)

    if (!familiesFilter || !FAMILY_FILTER_LOOKUP[familiesFilter]) {
      return searchedFamilies
    }

    const familyFilter = FAMILY_FILTER_LOOKUP[familiesFilter](individualsByGuid, samplesByGuid, user)
    return searchedFamilies.filter(familyFilter)
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
  getProjectFamiliesByGuid,
  getProjectIndividualsByGuid,
  getProjectSamplesByGuid,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilies, familiesByGuid, individualsByGuid, samplesByGuid, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder]) {
      return visibleFamilies
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](individualsByGuid, samplesByGuid)

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
  getProjectIndividualsByGuid,
  getProjectSamplesByGuid,
  (visibleFamilies, individualsByGuid, samplesByGuid) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivSortKey = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0

    return visibleFamilies.map((family) => {
      const familyIndividuals = orderBy(family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]), [getIndivSortKey])

      const familySamples = familySamplesLoaded(family, individualsByGuid, samplesByGuid)

      return Object.assign(family, {
        individuals: familyIndividuals,
        firstSample: familySamples.length > 0 ? familySamples[0] : null,
      })
    })
  },
)

export const getFamiliesExportConfig = createSelector(
  getProject,
  getVisibleSortedFamiliesWithIndividuals,
  (project, families) => ({
    filename: `${project.name.replace(' ', '_').toLowerCase()}_families`,
    rawData: families,
    headers: FAMILY_EXPORT_DATA.map(config => config.header),
    processRow: family => FAMILY_EXPORT_DATA.map((config) => {
      const val = family[config.field]
      return config.format ? config.format(val) : val
    }),
  }),
)

export const getIndividualsExportConfig = createSelector(
  getProject,
  getVisibleSortedFamiliesWithIndividuals,
  (project, families) => ({
    filename: `${project.name.replace(' ', '_').toLowerCase()}_individuals`,
    rawData: families.reduce((acc, family) =>
      [...acc, ...family.individuals.map(individual => ({ ...individual, familyId: family.familyId }))], [],
    ),
    headers: INDIVIDUAL_EXPORT_DATA.map(config => config.header),
    processRow: individual => INDIVIDUAL_EXPORT_DATA.map((config) => {
      const val = individual[config.field]
      return config.format ? config.format(val) : val
    }),
  }),
)

export const getCaseReviewStatusCounts = createSelector(
  getProjectIndividualsByGuid,
  (individualsByGuid) => {
    const caseReviewStatusCounts = Object.values(individualsByGuid).reduce((acc, individual) => ({
      ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1,
    }), {})

    return CASE_REVIEW_STATUS_OPTIONS.map(option => (
      { ...option, count: (caseReviewStatusCounts[option.value] || 0) }),
    )
  })

export const getAnalysisStatusCounts = createSelector(
  getProjectFamiliesByGuid,
  (familiesByGuid) => {
    const analysisStatusCounts = Object.values(familiesByGuid).reduce((acc, family) => ({
      ...acc, [family.analysisStatus]: (acc[family.analysisStatus] || 0) + 1,
    }), {})

    return FAMILY_ANALYSIS_STATUS_OPTIONS.map(option => (
      { ...option, count: (analysisStatusCounts[option.value] || 0) }),
    )
  })
