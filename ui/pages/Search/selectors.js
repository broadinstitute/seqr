import { createSelector, createSelectorCreator, defaultMemoize } from 'reselect'
import uniqWith from 'lodash/uniqWith'

import {
  getProjectsByGuid,
  getFamiliesByGuid,
  getFamiliesGroupedByProjectGuid,
  getCurrentAnalysisGroupFamilyGuids,
  getLocusListsByGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getUser,
  getSearchFamiliesByHash,
  getGenesById,
  getSearchesByHash,
  getSamplesGroupedByProjectGuid,
  getSamplesByFamily,
} from 'redux/selectors'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/utils/constants'
import { compareObjects } from 'shared/utils/sortUtils'
import { compHetGene } from 'shared/components/panel/variants/VariantUtils'

export const getSearchContextIsLoading = state => state.searchContextLoading.isLoading
export const getMultiProjectSearchContextIsLoading = state => state.multiProjectSearchContextLoading.isLoading
export const getSavedSearchesByGuid = state => state.savedSearchesByGuid
export const getSavedSearchesIsLoading = state => state.savedSearchesLoading.isLoading
export const getSavedSearchesLoadingError = state => state.savedSearchesLoading.errorMessage
export const getFlattenCompoundHet = state => state.flattenCompoundHet
export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchGeneBreakdown = state => state.searchGeneBreakdown
export const getSearchGeneBreakdownLoading = state => state.searchGeneBreakdownLoading.isLoading
export const getSearchGeneBreakdownErrorMessage = state => state.searchGeneBreakdownLoading.errorMessage
export const getVariantSearchDisplay = state => state.variantSearchDisplay

const getCurrentSearchHash = (state, ownProps) => ownProps.match.params.searchHash

export const getCurrentSearchParams = createSelector(
  getSearchesByHash,
  getCurrentSearchHash,
  (searchesByHash, searchHash) => searchesByHash[searchHash],
)

export const getTotalVariantsCount = createSelector(
  getCurrentSearchParams,
  searchParams => (searchParams || {}).totalResults,
)

export const getSearchedVariantExportConfig = createSelector(
  getCurrentSearchHash,
  getCurrentSearchParams,
  getProjectsByGuid,
  (searchHash, searchParams, projectsByGuid) => {
    const { projectFamilies } = searchParams || {}
    if ((projectFamilies || []).some(
      ({ projectGuid }) => projectsByGuid[projectGuid]?.isDemo && !projectsByGuid[projectGuid].allUserDemo,
    )) {
      // Do not allow downloads for demo projects
      return null
    }
    return [{
      name: 'Variant Search Results',
      url: `/api/search/${searchHash}/download`,
    }]
  },
)

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

const getSampleDatasetTypes = samples => ([
  ...new Set((samples || []).filter(({ isActive }) => isActive).map(({ datasetType }) => datasetType)),
])

export const getProjectDatasetTypes = createSelector(
  getProjectsByGuid,
  getSamplesGroupedByProjectGuid,
  (projectsByGuid, samplesByProjectGuid) => Object.values(projectsByGuid).reduce(
    (acc, { projectGuid, datasetTypes }) => ({
      ...acc,
      [projectGuid]: datasetTypes || getSampleDatasetTypes(Object.values(samplesByProjectGuid[projectGuid] || {})),
    }), {},
  ),
)

export const getDatasetTypes = createSelector(
  (state, props) => props.projectFamilies,
  getProjectDatasetTypes,
  getSamplesByFamily,
  (projectFamilies, projectDatasetTypes, samplesByFamily) => {
    const isSingleFamily = (projectFamilies || []).length === 1 && projectFamilies[0].familyGuids?.length === 1
    const datasetTypes = isSingleFamily ? getSampleDatasetTypes(samplesByFamily[projectFamilies[0].familyGuids[0]]) : (
      projectFamilies || []
    ).reduce((acc, { projectGuid }) => new Set([
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

export const getDisplayVariants = createSelector(
  getFlattenCompoundHet,
  getSearchedVariants,
  (flattenCompoundHet, searchedVariants) => {
    const shouldFlatten = Object.values(flattenCompoundHet || {}).some(val => val)
    if (!shouldFlatten) {
      return searchedVariants || []
    }
    const flattened = flattenCompoundHet.all ? searchedVariants.flat() : searchedVariants.reduce((acc, variant) => (
      (Array.isArray(variant) && flattenCompoundHet[compHetGene(variant)]) ? [...acc, ...variant] : [...acc, variant]
    ), [])
    return uniqWith(flattened, (a, b) => !Array.isArray(a) && !Array.isArray(b) && a.variantId === b.variantId)
  },
)

export const getSearchGeneBreakdownValues = createSelector(
  getSearchGeneBreakdown,
  (state, props) => props.searchHash,
  getFamiliesByGuid,
  getGenesById,
  getSearchesByHash,
  (geneBreakdowns, searchHash, familiesByGuid, genesById, searchesByHash) => Object.entries(
    geneBreakdowns[searchHash] || {},
  ).map(([geneId, counts]) => ({
    numVariants: counts.total,
    numFamilies: Object.keys(counts.families).length,
    families: Object.entries(counts.families).map(
      ([familyGuid, count]) => ({ family: familiesByGuid[familyGuid], count }),
    ),
    search: searchesByHash[searchHash].search,
    ...(genesById[geneId] || { geneId, geneSymbol: geneId, omimPhenotypes: [], constraints: {} }),
  })),
)
