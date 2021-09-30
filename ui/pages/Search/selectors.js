import { createSelector, createSelectorCreator, defaultMemoize } from 'reselect'
import { formValueSelector } from 'redux-form'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsByGuid,
  getLocusListsByGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getCurrentSearchParams,
  getSamplesGroupedByProjectGuid,
  getUser,
} from 'redux/selectors'
import { compareObjects } from 'shared/utils/sortUtils'
import { SEARCH_FORM_NAME } from './constants'

export const getSearchContextIsLoading = state => state.searchContextLoading.isLoading
export const getMultiProjectSearchContextIsLoading = state => state.multiProjectSearchContextLoading.isLoading
export const getSavedSearchesByGuid = state => state.savedSearchesByGuid
export const getSavedSearchesIsLoading = state => state.savedSearchesLoading.isLoading
export const getSavedSearchesLoadingError = state => state.savedSearchesLoading.errorMessage
export const getFlattenCompoundHet = state => state.flattenCompoundHet

export const getInhertanceFilterMode = createSelector(
  getCurrentSearchParams,
  searchParams => (((searchParams || {}).search || {}).inheritance || {}).mode,
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
  } else if (params.searchHash) {
    return params
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
  (savedSearches) => {
    const savedSeachOptions = savedSearches.map(({ name, savedSearchGuid, createdById }) => (
      { text: name, value: savedSearchGuid, category: createdById ? 'My Searches' : 'Default Searches' }
    ))
    savedSeachOptions.push({ text: 'None', value: null, category: 'Default Searches', search: {} })
    return savedSeachOptions.sort(compareObjects('text')).sort(compareObjects('category'))
  },
)

const getProjectsInput = createSelector(
  getProjectsFamiliesFieldInput,
  projectFamilies => (projectFamilies || []).map(({ projectGuid }) => projectGuid),
)

export const getInputProjectsCount = createSelector(
  getProjectsFamiliesFieldInput,
  projectFamilies => (projectFamilies || []).length,
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

export const getDatasetTypes = createSelector(
  getProjectsInput,
  getSamplesGroupedByProjectGuid,
  (projectGuids, samplesByProjectGuid) => {
    const datasetTypes = projectGuids.reduce((acc, projectGuid) =>
      new Set([...acc, ...Object.values(samplesByProjectGuid[projectGuid] || {}).filter(
        ({ isActive }) => isActive).map(({ datasetType }) => datasetType)]), new Set())
    return [...datasetTypes].sort().join(',')
  },
)

export const getHasHgmdPermission = createSelector(
  getUser,
  getProjectsInput,
  getProjectsByGuid,
  (user, projectGuids, projectsByGuid) => user.isAnalyst || projectGuids.some(
    projectGuid => (projectsByGuid[projectGuid] || {}).enableHgmd),
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
