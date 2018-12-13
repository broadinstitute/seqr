import { createSelector } from 'reselect'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  getLocusListsByGuid,
} from 'redux/selectors'
import { getVariantsExportData } from 'shared/utils/constants'

export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchesByHash = state => state.searchesByHash
export const getVariantSearchDisplay = state => state.variantSearchDisplay

const getQueryParams = (state, props) => props.queryParams

export const getCurrentSearchParams = createSelector(
  getSearchesByHash,
  getQueryParams,
  (searchesByHash, queryParams) => searchesByHash[queryParams.search],
)

export const getLoadedIntitialSearch = createSelector(
  getQueryParams,
  getCurrentSearchParams,
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  (queryParams, searchParams, projectsByGuid, familiesByGuid, familiesByProjectGuid, analysisGroupByGuid) => {

    if (searchParams) {
      return searchParams.searchedProjectFamilies.every(
        ({ projectGuid }) => projectsByGuid[projectGuid],
      ) ? searchParams : null
    }

    let searchedProjectFamilies
    if (queryParams.projectGuid && familiesByProjectGuid[queryParams.projectGuid]) {
      searchedProjectFamilies = [{
        projectGuid: queryParams.projectGuid,
        familyGuids: Object.keys(familiesByProjectGuid[queryParams.projectGuid]),
      }]
    }
    else if (queryParams.familyGuid && familiesByGuid[queryParams.familyGuid]) {
      searchedProjectFamilies = [{
        projectGuid: familiesByGuid[queryParams.familyGuid].projectGuid,
        familyGuids: [queryParams.familyGuid],
      }]
    }
    else if (queryParams.analysisGroupGuid && analysisGroupByGuid[queryParams.analysisGroupGuid]) {
      searchedProjectFamilies = [{
        projectGuid: analysisGroupByGuid[queryParams.analysisGroupGuid].projectGuid,
        familyGuids: analysisGroupByGuid[queryParams.analysisGroupGuid].familyGuids,
      }]
    }

    return searchedProjectFamilies ? { searchedProjectFamilies } : null
  },
)

export const getTotalVariantsCount = createSelector(
  getCurrentSearchParams,
  searchParams => (searchParams || {}).totalResults,
)

export const getSearchedVariantExportConfig = createSelector(
  getSearchedVariants,
  variants => [{
    name: 'Variant Search Results',
    data: {
      filename: 'searched_variants',
      ...getVariantsExportData(variants),
    },
  }],
)

export const getSearchedProjectsLocusLists = createSelector(
  (state, props) => props.familyGuid,
  getProjectsByGuid,
  getFamiliesByGuid,
  getLocusListsByGuid,
  (familyGuid, projectsByGuid, familiesByGuid, locusListsByGuid) => (
    projectsByGuid[familiesByGuid[familyGuid]] ?
      projectsByGuid[familiesByGuid[familyGuid]].locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid])
      : []),
)
