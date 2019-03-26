import { createSelector } from 'reselect'
import { formValueSelector } from 'redux-form'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  getLocusListsByGuid,
} from 'redux/selectors'
import { SEARCH_FORM_NAME } from './constants'


export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchContextIsLoading = state => state.searchContextLoading.isLoading
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

export const getProjectsFamiliesFieldInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'projectFamilies')

export const getSearchInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'search')

export const getCurrentSavedSearch = createSelector(
  getSearchInput,
  getSavedSearchesByGuid,
  (search, savedSearchesByGuid) =>
    Object.values(savedSearchesByGuid).find(savedSearch => savedSearch.search === search),
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

export const getSearchedProjectsLocusLists = createSelector(
  getProjectsFamiliesFieldInput,
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectFamilies, projectsByGuid, locusListsByGuid) => {
    const locusListGuids = [...new Set((projectFamilies || []).reduce((acc, { projectGuid }) => (
      projectsByGuid[projectGuid] ? [...acc, ...projectsByGuid[projectGuid].locusListGuids] : acc), [],
    ))]
    return locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid])
  },
)
