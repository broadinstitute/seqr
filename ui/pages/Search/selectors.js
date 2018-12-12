import { createSelector } from 'reselect'

import { getProjectsByGuid, getFamiliesByGuid, getLocusListsByGuid } from 'redux/selectors'
import { getVariantsExportData } from 'shared/utils/constants'

export const getSearchedProjectIsLoading = state => state.searchedProjectLoading.isLoading
export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchesByHash = state => state.searchesByHash
export const getVariantSearchDisplay = state => state.variantSearchDisplay

export const getCurrentSearchParams = createSelector(
  getSearchesByHash,
  (state, props) => props.queryParams.search,
  (searchesByHash, searchHash) => searchesByHash[searchHash],
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
