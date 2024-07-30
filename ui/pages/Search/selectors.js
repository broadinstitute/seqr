import { createSelector, createSelectorCreator, defaultMemoize } from 'reselect'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getCurrentAnalysisGroupFamilyGuids,
  getLocusListsByGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getCurrentSearchParams,
  getUser,
  getProjectDatasetTypes,
  getSearchFamiliesByHash,
} from 'redux/selectors'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/utils/constants'
import { compareObjects } from 'shared/utils/sortUtils'

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

export const getProjectFamilies = createSelector(
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getCurrentAnalysisGroupFamilyGuids,
  (familiesByGuid, familiesByProjectGuid, analysisGroupFamilyGuids) => (
    { projectGuid, familyGuids, familyGuid, analysisGroupGuid, searchHash, ...params },
  ) => {
    if (projectGuid && familyGuids) {
      return { projectGuid, familyGuids }
    }

    if (analysisGroupGuid) {
      return analysisGroupFamilyGuids ? {
        projectGuid,
        familyGuids: analysisGroupFamilyGuids,
      } : { projectGuid, analysisGroupGuid }
    }
    if (projectGuid) {
      const loadedProjectFamilies = familiesByProjectGuid[projectGuid]
      return {
        projectGuid,
        familyGuids: loadedProjectFamilies ? Object.keys(loadedProjectFamilies) : null,
      }
    }
    if (familyGuid || familyGuids) {
      const singleFamilyGuid = familyGuid || familyGuids[0]
      return {
        projectGuid: (familiesByGuid[singleFamilyGuid] || {}).projectGuid,
        familyGuids: [singleFamilyGuid],
      }
    }
    if (searchHash) {
      return { projectGuid, familyGuids, familyGuid, analysisGroupGuid, searchHash, ...params }
    }
    return null
  },
)

export const getMultiProjectFamilies = createSelector(
  (state, props) => props.match.params,
  getSearchFamiliesByHash,
  (params, searchFamiliesByHash) => ({
    projectFamilies: Object.entries(searchFamiliesByHash[params.familiesHash] || {}).map(
      ([projectGuid, familyGuids]) => ({ projectGuid, familyGuids }),
    ),
  }),
)

const createProjectFamiliesSelector = createSelectorCreator(
  defaultMemoize,
  (a, b) => ['projectGuid', 'familyGuids', 'familyGuid', 'analysisGroupGuid', 'searchHash'].every(k => a[k] === b[k]),
)

const getIntitialProjectFamilies = createProjectFamiliesSelector(
  (state, props) => props.match.params,
  getProjectFamilies,
  (params, getProjectFamiliesFunc) => getProjectFamiliesFunc(params),
)

export const getIntitialSearch = createSelector(
  getCurrentSearchParams,
  getIntitialProjectFamilies,
  (searchParams, projectFamilies) => {
    if (searchParams) {
      return searchParams
    }

    return projectFamilies ? { projectFamilies: [projectFamilies] } : null
  },
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
    const savedSeachOptions = savedSearches.sort(compareObjects('name')).sort(compareObjects('order')).map(
      ({ name, savedSearchGuid, createdById }) => (
        { text: name, value: savedSearchGuid, category: createdById ? 'My Searches' : 'Default Searches' }
      ),
    )
    savedSeachOptions.push({ text: 'None', value: null, category: 'Default Searches', search: {} })
    return savedSeachOptions.sort(compareObjects('category'))
  },
)

export const getLocusListOptions = createListEqualSelector(
  (state, props) => props.projectFamilies,
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectFamilies, projectsByGuid, locusListsByGuid) => {
    const projectsLocusListGuids = new Set((projectFamilies || []).reduce(
      (acc, { projectGuid }) => ((projectsByGuid[projectGuid] || {}).locusListGuids ?
        [...acc, ...projectsByGuid[projectGuid].locusListGuids] : acc), [],
    ))
    return Object.values(locusListsByGuid).map(({ locusListGuid, name, numEntries, isPublic, paLocusList }) => ({
      text: name,
      value: locusListGuid,
      key: locusListGuid,
      description: `${numEntries} Genes${paLocusList ? ' - PanelApp' : ''}`,
      icon: { name: isPublic ? 'users' : 'lock', size: 'small' },
      category: `${projectsLocusListGuids.has(locusListGuid) ? 'Project' : 'All'} Lists`,
      categoryRank: projectsLocusListGuids.has(locusListGuid) ? 0 : 1,
    })).sort(compareObjects('text')).sort(compareObjects('categoryRank'))
  },
)

export const getDatasetTypes = createSelector(
  (state, props) => props.projectFamilies,
  getProjectDatasetTypes,
  (projectFamilies, projectDatasetTypes) => {
    const datasetTypes = (projectFamilies || []).reduce((acc, { projectGuid }) => new Set([
      ...acc, ...(projectDatasetTypes[projectGuid] || [])]), new Set())
    return [...datasetTypes].sort().join(',')
  },
)

export const getHasHgmdPermission = createSelector(
  getUser,
  (state, props) => props.projectFamilies,
  getProjectsByGuid,
  (user, projectFamilies, projectsByGuid) => user.isAnalyst || (projectFamilies || []).some(
    ({ projectGuid }) => (projectsByGuid[projectGuid] || {}).enableHgmd,
  ),
)

export const getFamilyOptions = createSelector(
  getFamiliesGroupedByProjectGuid,
  (state, props) => props.value.projectGuid,
  (familesGroupedByProjectGuid, projectGuid) => Object.values(familesGroupedByProjectGuid[projectGuid] || {}).map(
    ({ familyGuid, displayName, analysisStatus }) => ({
      value: familyGuid,
      text: displayName,
      analysisStatus,
      color: FAMILY_ANALYSIS_STATUS_LOOKUP[analysisStatus].color,
    }),
  ),
)

export const getAnalysisGroupOptions = createSelector(
  getAnalysisGroupsGroupedByProjectGuid,
  (state, props) => props.value.projectGuid,
  (analysisGroupsGroupedByProjectGuid, projectGuid) => Object.values({
    ...(analysisGroupsGroupedByProjectGuid[projectGuid] || {}),
    ...(analysisGroupsGroupedByProjectGuid.null || {}),
  }).map(group => ({ value: group.analysisGroupGuid, text: group.name, icon: group.criteria ? 'sync' : null })),
)
