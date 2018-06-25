import orderBy from 'lodash/orderBy'
import { createSelector } from 'reselect'

import { getSearchResults } from 'redux/utils/reduxSearchEnhancer'
import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/utils/constants'

import {
  getProjectsByGuid, getFamiliesByGuid, getIndividualsByGuid, getSamplesByGuid, getDatasetsByGuid, getUser,
} from 'redux/selectors'

import {
  SHOW_ALL,
  SORT_BY_FAMILY_NAME,
  CASE_REVIEW_STATUS_OPTIONS,
  FAMILY_FILTER_OPTIONS,
  FAMILY_SORT_OPTIONS,
  FAMILY_EXPORT_DATA,
  SORT_BY_FAMILY_GUID,
  VARIANT_SORT_OPTONS,
  VARIANT_EXPORT_DATA,
  VARIANT_GENOTYPE_EXPORT_DATA, ANALYSIS_TYPE_VARIANT_CALLS,
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
export const getVisibleFamilies = createSelector(
  getProjectFamilies,
  getIndividualsByGuid,
  getSamplesByGuid,
  getDatasetsByGuid,
  getUser,
  getFamiliesFilter,
  getSearchResults('familiesByGuid'),
  (families, individualsByGuid, samplesByGuid, datsetsByGuid, user, familiesFilter, familySearchResults) => {
    const searchedFamilies = families.filter(family => familySearchResults.includes(family.familyGuid))

    if (!familiesFilter || !FAMILY_FILTER_LOOKUP[familiesFilter]) {
      return searchedFamilies
    }

    const familyFilter = FAMILY_FILTER_LOOKUP[familiesFilter](individualsByGuid, samplesByGuid, datsetsByGuid, user)
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
  getIndividualsByGuid,
  getSamplesByGuid,
  getDatasetsByGuid,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilies, individualsByGuid, samplesByGuid, datsetsByGuid, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder]) {
      return visibleFamilies
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](individualsByGuid, samplesByGuid, datsetsByGuid)

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
  getIndividualsByGuid,
  getProjectSamples,
  getProjectDatasets,
  (visibleFamilies, individualsByGuid, samples, datasets) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivSortKey = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0

    return visibleFamilies.map((family) => {
      const familyIndividuals = orderBy(family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]), [getIndivSortKey])

      const familyDatasetGuids = samples.filter(s => family.individualGuids.includes(s.individualGuid)).reduce(
        (acc, sample) => new Set([...acc, ...sample.datasetGuids]), new Set(),
      )
      let loadedDatasets = datasets.filter(dataset => (
        familyDatasetGuids.has(dataset.datasetGuid) &&
        dataset.analysisType === ANALYSIS_TYPE_VARIANT_CALLS &&
        dataset.isLoaded
      ))
      loadedDatasets = orderBy(loadedDatasets, [d => d.loadedDate], 'asc')

      return Object.assign(family, {
        individuals: familyIndividuals,
        firstDataset: loadedDatasets.length > 0 ? loadedDatasets[0] : null,
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
