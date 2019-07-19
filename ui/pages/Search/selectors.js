import { createSelector, createSelectorCreator, defaultMemoize } from 'reselect'
import { formValueSelector } from 'redux-form'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  getLocusListsByGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getGenesById,
} from 'redux/selectors'
import { compareObjects } from 'shared/utils/sortUtils'
import { SEARCH_FORM_NAME } from './constants'


export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchGeneBreakdown = state => state.searchGeneBreakdown
export const getSearchGeneBreakdownLoading = state => state.searchGeneBreakdownLoading.isLoading
export const getSearchGeneBreakdownErrorMessage = state => state.searchGeneBreakdownLoading.errorMessage

export const getSearchContextIsLoading = state => state.searchContextLoading.isLoading
export const getMultiProjectSearchContextIsLoading = state => state.multiProjectSearchContextLoading.isLoading
export const getSearchesByHash = state => state.searchesByHash
export const getSavedSearchesByGuid = state => state.savedSearchesByGuid
export const getSavedSearchesIsLoading = state => state.savedSearchesLoading.isLoading
export const getSavedSearchesLoadingError = state => state.savedSearchesLoading.errorMessage
export const getVariantSearchDisplay = state => state.variantSearchDisplay

const getCurrentSearchHash = state => state.currentSearchHash

export const getCurrentSearchParams = createSelector(
  getSearchesByHash,
  getCurrentSearchHash,
  (searchesByHash, searchHash) => searchesByHash[searchHash],
)

export const getProjectFamilies = (params, familiesByGuid, familiesByProjectGuid, analysisGroupByGuid) => {
  if (params.projectGuid && params.familyGuids) {
    return params
  }

  if (params.projectGuid) {
    const loadedProjectFamilies = familiesByProjectGuid[params.projectGuid]
    return {
      projectGuid: params.projectGuid,
      familyGuids: loadedProjectFamilies ? Object.keys(loadedProjectFamilies) : null,
    }
  }
  else if (params.analysisGroupGuid) {
    const analysisGroup = analysisGroupByGuid[params.analysisGroupGuid]
    return analysisGroup ? {
      projectGuid: analysisGroup.projectGuid,
      familyGuids: analysisGroup.familyGuids,
    } : { analysisGroupGuid: params.analysisGroupGuid }
  } else if (params.familyGuid || params.familyGuids) {
    const familyGuid = params.familyGuid || params.familyGuids[0]
    return {
      projectGuid: (familiesByGuid[familyGuid] || {}).projectGuid,
      familyGuids: [familyGuid],
    }
  }
  return null
}

export const getIntitialSearch = createSelector(
  (state, props) => props.match.params,
  getCurrentSearchParams,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  (urlParams, searchParams, familiesByGuid, familiesByProjectGuid, analysisGroupByGuid) => {

    if (searchParams) {
      return searchParams
    }

    const projectFamilies = getProjectFamilies(urlParams, familiesByGuid, familiesByProjectGuid, analysisGroupByGuid)

    return projectFamilies ? { projectFamilies: [projectFamilies] } : null
  },
)

const getProjectsFamiliesFieldInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'projectFamilies')

export const getSearchInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'search')

export const getCurrentSavedSearch = createSelector(
  getSearchInput,
  getSavedSearchesByGuid,
  (search, savedSearchesByGuid) =>
    Object.values(savedSearchesByGuid).find(savedSearch => savedSearch.search === search),
)

const createListEqualSelector = createSelectorCreator(
  defaultMemoize,
  (a, b) => (
    Array.isArray(a) ? (a.length === b.length && Object.entries(a).every(([i, val]) => val === b[i])) : a === b
  ),
)

const getSavedSearches = createSelector(
  getSavedSearchesByGuid,
  savedSearchesByGuid => Object.values(savedSearchesByGuid),
)

const createSavedSearchesSelector = createSelectorCreator(
  defaultMemoize,
  (a, b) => (
    a.length === b.length && Object.entries(a).every(
      ([i, val]) => val.savedSearchGuid === b[i].savedSearchGuid,
    )),
)

export const getSavedSearchOptions = createSavedSearchesSelector(
  getSavedSearches,
  savedSearches => savedSearches.map(({ name, savedSearchGuid, createdById }) => (
    { text: name, value: savedSearchGuid, category: createdById ? 'My Searches' : 'Default Searches' }
  )).sort(compareObjects('text')).sort(compareObjects('category')),
)

export const getTotalVariantsCount = createSelector(
  getCurrentSearchParams,
  searchParams => (searchParams || {}).totalResults,
)

export const getSearchedVariantExportConfig = createSelector(
  getCurrentSearchHash,
  searchHash => [{
    name: 'Variant Search Results',
    url: `/api/search/${searchHash}/download`,
  }],
)

const getProjectsInput = createSelector(
  getProjectsFamiliesFieldInput,
  projectFamilies => (projectFamilies || []).map(({ projectGuid }) => projectGuid),
)

export const getSearchedProjectsLocusListOptions = createListEqualSelector(
  getProjectsInput,
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectGuids, projectsByGuid, locusListsByGuid) => {
    const locusListGuids = [...new Set((projectGuids || []).reduce((acc, projectGuid) => (
      projectsByGuid[projectGuid] ? [...acc, ...projectsByGuid[projectGuid].locusListGuids] : acc), [],
    ))]
    const locusListOptions = locusListGuids.map(locusListGuid => (
      { text: locusListsByGuid[locusListGuid].name, value: locusListsByGuid[locusListGuid].locusListGuid }
    ))
    return [{ value: null }, ...locusListOptions]
  },
)

const getSingleFamlilyGuidInput = createSelector(
  getProjectsFamiliesFieldInput,
  projectFamilies => (
    (projectFamilies && projectFamilies.length === 1 && (projectFamilies[0].familyGuids || []).length === 1) ?
      projectFamilies[0].familyGuids[0] : null
  ),
)

export const getSingleInputFamily = createSelector(
  getSingleFamlilyGuidInput,
  getFamiliesByGuid,
  (familyGuid, familiesByGuid) => familiesByGuid[familyGuid],
)

export const getFamilyOptions = createSelector(
  getFamiliesGroupedByProjectGuid,
  (state, props) => props.value.projectGuid,
  (familesGroupedByProjectGuid, projectGuid) => Object.values(familesGroupedByProjectGuid[projectGuid] || {}).map(
    family => ({ value: family.familyGuid, text: family.displayName }),
  ),
)

export const getAnalysisGroupOptions = createSelector(
  getAnalysisGroupsGroupedByProjectGuid,
  (state, props) => props.value.projectGuid,
  (analysisGroupsGroupedByProjectGuid, projectGuid) =>
    Object.values(analysisGroupsGroupedByProjectGuid[projectGuid] || {}).map(
      group => ({ value: group.analysisGroupGuid, text: group.name }),
    ),
)

export const getSearchGeneBreakdownValues = createSelector(
  getSearchGeneBreakdown,
  (state, props) => props.searchHash,
  getFamiliesByGuid,
  getGenesById,
  getSearchesByHash,
  (geneBreakdowns, searchHash, familiesByGuid, genesById, searchesByHash) =>
    Object.entries(geneBreakdowns[searchHash] || {}).map(
      ([geneId, counts]) => ({
        numVariants: counts.total,
        numFamilies: Object.keys(counts.families).length,
        families: Object.entries(counts.families).map(([familyGuid, count]) => ({ family: familiesByGuid[familyGuid], count })),
        search: searchesByHash[searchHash].search,
        ...genesById[geneId],
      }),
    ),
)
