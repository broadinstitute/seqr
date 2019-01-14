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

export const getLoadedIntitialSearch = createSelector(
  (state, props) => props.match.params,
  getCurrentSearchParams,
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  (urlParams, searchParams, projectsByGuid, familiesByGuid, familiesByProjectGuid, analysisGroupByGuid) => {

    if (searchParams) {
      return searchParams.projectFamilies.every(
        ({ projectGuid }) => projectsByGuid[projectGuid],
      ) ? searchParams : null
    }

    let projectFamilies
    if (urlParams.projectGuid && familiesByProjectGuid[urlParams.projectGuid]) {
      projectFamilies = [{
        projectGuid: urlParams.projectGuid,
        familyGuids: Object.keys(familiesByProjectGuid[urlParams.projectGuid]),
      }]
    }
    else if (urlParams.familyGuid && familiesByGuid[urlParams.familyGuid]) {
      projectFamilies = [{
        projectGuid: familiesByGuid[urlParams.familyGuid].projectGuid,
        familyGuids: [urlParams.familyGuid],
      }]
    }
    else if (urlParams.analysisGroupGuid && analysisGroupByGuid[urlParams.analysisGroupGuid]) {
      projectFamilies = [{
        projectGuid: analysisGroupByGuid[urlParams.analysisGroupGuid].projectGuid,
        familyGuids: analysisGroupByGuid[urlParams.analysisGroupGuid].familyGuids,
      }]
    }

    return projectFamilies ? { projectFamilies } : null
  },
)

export const getProjectsFamiliesFieldInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'projectFamilies')

export const getSearchInput = state =>
  formValueSelector(SEARCH_FORM_NAME)(state, 'search')

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
    const locusListGuids = [...new Set(projectFamilies.reduce((acc, { projectGuid }) => (
      projectsByGuid[projectGuid] ? [...acc, ...projectsByGuid[projectGuid].locusListGuids] : acc), [],
    ))]
    return locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid])
  },
)
