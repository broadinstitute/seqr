import { createSelector } from 'reselect'
import uniqBy from 'lodash/uniqBy'

import { compareObjects } from 'shared/utils/sortUtils'
import { NOTE_TAG_NAME } from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getIgvSamplesByGuid = state => state.igvSamplesByGuid
export const getAnalysisGroupsByGuid = state => state.analysisGroupsByGuid
export const getSavedVariantsByGuid = state => state.savedVariantsByGuid
export const getVariantTagsByGuid = state => state.variantTagsByGuid
export const getVariantNotesByGuid = state => state.variantNotesByGuid
export const getVariantFunctionalDataByGuid = state => state.variantFunctionalDataByGuid
export const getMmeSubmissionsByGuid = state => state.mmeSubmissionsByGuid
export const getMmeResultsByGuid = state => state.mmeResultsByGuid
export const getGenesById = state => state.genesById
export const getPaGenesById = state => state.pagenesById
export const getGenesIsLoading = state => state.genesLoading.isLoading
export const getHpoTermsByParent = state => state.hpoTermsByParent
export const getHpoTermsIsLoading = state => state.hpoTermsLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getUser = state => state.user
export const getUserOptionsByUsername = state => state.userOptionsByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getVersion = state => state.meta.version
export const getGoogleLoginEnabled = state => state.meta.googleLoginEnabled
export const getHijakEnabled = state => state.meta.hijakEnabled
export const getSavedVariantsIsLoading = state => state.savedVariantsLoading.isLoading
export const getSavedVariantsLoadingError = state => state.savedVariantsLoading.errorMessage
export const getSearchesByHash = state => state.searchesByHash
export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getSearchGeneBreakdown = state => state.searchGeneBreakdown
export const getSearchGeneBreakdownLoading = state => state.searchGeneBreakdownLoading.isLoading
export const getSearchGeneBreakdownErrorMessage = state => state.searchGeneBreakdownLoading.errorMessage
export const getVariantSearchDisplay = state => state.variantSearchDisplay

export const getAnnotationSecondary = (state) => {
  try {
    return !!state.form.variantSearch.values.search.inheritance.annotationSecondary
  }
  catch (err) {
    return false
  }
}

const groupEntitiesByProjectGuid = entities => Object.entries(entities).reduce((acc, [entityGuid, entity]) => {
  if (!(entity.projectGuid in acc)) {
    acc[entity.projectGuid] = {}
  }
  acc[entity.projectGuid][entityGuid] = entity

  return acc

}, {})
export const getFamiliesGroupedByProjectGuid = createSelector(getFamiliesByGuid, groupEntitiesByProjectGuid)
export const getAnalysisGroupsGroupedByProjectGuid = createSelector(getAnalysisGroupsByGuid, groupEntitiesByProjectGuid)
export const getSamplesGroupedByProjectGuid = createSelector(getSamplesByGuid, groupEntitiesByProjectGuid)

const groupIndividualsByFamilyGuid = individuals =>
  individuals.reduce((acc, individual) => {
    if (!acc[individual.familyGuid]) {
      acc[individual.familyGuid] = []
    }
    acc[individual.familyGuid].push(individual)
    return acc
  }, {})

export const getIndividualsByFamily = createSelector(
  getIndividualsByGuid,
  individualsByGuid => groupIndividualsByFamilyGuid(Object.values(individualsByGuid)),
)

const getSortedIndividuals = createSelector(
  getIndividualsByGuid,
  getMmeSubmissionsByGuid,
  (individualsByGuid, mmeSubmissionsByGuid) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivAffectedSort = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0
    const getIndivMmeSort = ({ mmeSubmissionGuid }) => {
      const { deletedDate, createdDate = '1900-01-01' } = mmeSubmissionsByGuid[mmeSubmissionGuid] || {}
      return deletedDate ? '2000-01-01' : createdDate
    }

    return Object.values(individualsByGuid).sort((a, b) => {
      const compareVal = getIndivAffectedSort(a) - getIndivAffectedSort(b)
      if (compareVal === 0) {
        return getIndivMmeSort(b).localeCompare(getIndivMmeSort(a))
      }
      return compareVal
    })
  },
)

export const getSortedIndividualsByFamily = createSelector(
  getSortedIndividuals,
  groupIndividualsByFamilyGuid,
)

const getSortedSamples = createSelector(
  getSamplesByGuid,
  samplesByGuid => Object.values(samplesByGuid).sort((a, b) => a.loadedDate.localeCompare(b.loadedDate)),
)

export const getSamplesByFamily = createSelector(
  getIndividualsByGuid,
  getSortedSamples,
  (individualsByGuid, sortedSamples) =>
    sortedSamples.reduce((acc, sample) => {
      const { familyGuid } = individualsByGuid[sample.individualGuid]
      if (!acc[familyGuid]) {
        acc[familyGuid] = []
      }
      acc[familyGuid].push(sample)
      return acc
    }, {}),
)

export const getHasActiveVariantSampleByFamily = createSelector(
  getSamplesByFamily,
  (samplesByFamily) => {
    return Object.entries(samplesByFamily).reduce((acc, [familyGuid, familySamples]) => ({
      ...acc,
      [familyGuid]: familySamples.some(({ isActive }) => isActive),
    }), {})
  },
)

export const getIGVSamplesByFamilySampleIndividual = createSelector(
  getIndividualsByGuid,
  getIgvSamplesByGuid,
  (individualsByGuid, igvSamplesByGuid) =>
    Object.values(igvSamplesByGuid).reduce((acc, sample) => {
      const { familyGuid } = individualsByGuid[sample.individualGuid]
      if (!acc[familyGuid]) {
        acc[familyGuid] = {}
      }
      if (!acc[familyGuid][sample.sampleType]) {
        acc[familyGuid][sample.sampleType] = {}
      }
      acc[familyGuid][sample.sampleType][sample.individualGuid] = sample
      return acc
    }, {}),
)

// Saved variant selectors
const groupByVariantGuids = allObjects =>
  Object.values(allObjects).reduce((acc, o) => {
    const variantGuids = o.variantGuids.sort().join(',')
    if (!acc[variantGuids]) {
      acc[variantGuids] = []
    }
    acc[variantGuids].push(o)
    return acc
  }, {})

export const getTagsByVariantGuids = createSelector(
  getVariantTagsByGuid,
  groupByVariantGuids,
)

export const getNotesByVariantGuids = createSelector(
  getVariantNotesByGuid,
  groupByVariantGuids,
)

const getFunctionalDataByVariantGuids = createSelector(
  getVariantFunctionalDataByGuid,
  groupByVariantGuids,
)

export const getVariantId = variant =>
  (Array.isArray(variant) ? variant : [variant]).map(({ variantId }) => variantId).sort().join(',')

export const getVariantTagNotesByFamilyVariants = createSelector(
  getTagsByVariantGuids,
  getNotesByVariantGuids,
  getFunctionalDataByVariantGuids,
  getSavedVariantsByGuid,
  (tagsByGuids, notesByGuids, functionalDataByGuids, savedVariantsByGuid) => {
    let variantDetails = Object.entries(tagsByGuids).reduce(
      (acc, [variantGuids, tags]) => ({ ...acc, [variantGuids]: { tags, variantGuids } }), {})

    variantDetails = Object.entries(notesByGuids).reduce((acc, [variantGuids, notes]) => {
      if (!acc[variantGuids]) {
        acc[variantGuids] = { variantGuids }
      }
      acc[variantGuids].notes = notes
      return acc
    }, variantDetails)

    variantDetails = Object.entries(functionalDataByGuids).reduce((acc, [variantGuids, functionalData]) => {
      if (!acc[variantGuids]) {
        acc[variantGuids] = { variantGuids }
      }
      acc[variantGuids].functionalData = functionalData
      return acc
    }, variantDetails)

    variantDetails = Object.keys(savedVariantsByGuid).reduce((acc, variantGuid) => {
      if (!acc[variantGuid]) {
        acc[variantGuid] = { variantGuids: variantGuid }
      }
      return acc
    }, variantDetails)

    return Object.values(variantDetails).reduce((acc, variantDetail) => {
      const variants = variantDetail.variantGuids.split(',').map(variantGuid => savedVariantsByGuid[variantGuid])
      const variantId = getVariantId(variants)
      variants[0].familyGuids.forEach((familyGuid) => {
        if (!(familyGuid in acc)) {
          acc[familyGuid] = {}
        }
        acc[familyGuid][variantId] = variantDetail
      })
      return acc
    }, {})
  },
)

export const getTagTypesByProject = createSelector(
  getProjectsByGuid,
  projectsByGuid => Object.values(projectsByGuid).reduce((acc, project) => ({
    ...acc,
    [project.projectGuid]: (project.variantTagTypes || []).filter(vtt => vtt.name !== NOTE_TAG_NAME),
  }), {}),
)

export const getFunctionalTagTypesTypesByProject = createSelector(
  getProjectsByGuid,
  projectsByGuid => Object.values(projectsByGuid).reduce((acc, project) => ({
    ...acc,
    [project.projectGuid]: project.variantFunctionalTagTypes,
  }), {}),
)

const getLocusListsWithGenes = createSelector(
  getLocusListsByGuid,
  getGenesById,
  (locusListsByGuid, genesById) =>
    Object.entries(locusListsByGuid).reduce((acc, [locusListGuid, locusList]) => ({
      ...acc,
      [locusListGuid]: {
        ...locusList,
        items: locusList.items && locusList.items.map(item => ({ ...item, gene: genesById[item.geneId] })),
      } }), {}),
)

export const getParsedLocusList = createSelector(
  getLocusListsWithGenes,
  (state, props) => props.locusListGuid,
  (locusListsByGuid, locusListGuid) => {
    const locusList = locusListsByGuid[locusListGuid] || {}
    if (locusList.items) {
      locusList.items = locusList.items.map((item) => {
        let display
        if (item.geneId) {
          display = item.gene ? item.gene.geneSymbol : item.geneId
        } else {
          display = `chr${item.chrom}:${item.start}-${item.end}`
        }
        return { ...item, display }
      })
      locusList.items.sort(compareObjects('display'))
      locusList.rawItems = locusList.items.map(({ display }) => display).join(', ')
    }
    return locusList
  },
)

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

export const getDisplayVariants = createSelector(
  (state, ownProps) => ownProps.flattenCompoundHet,
  getSearchedVariants,
  (flattenCompoundHet, searchedVariants) => (flattenCompoundHet ? (uniqBy(searchedVariants.flat(), 'variantId') || []) : searchedVariants),
)

export const getSearchedVariantExportConfig = createSelector(
  getCurrentSearchHash,
  searchHash => [{
    name: 'Variant Search Results',
    url: `/api/search/${searchHash}/download`,
  }],
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
        ...(genesById[geneId] || { geneId, geneSymbol: geneId, omimPhenotypes: [], constraints: {} }),
      }),
    ),
)

export const getLocusListIntervalsByChromProject = createSelector(
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectsByGuid, locusListsByGuid) =>
    Object.entries(projectsByGuid).reduce((acc, [projectGuid, { locusListGuids = [] }]) => {
      const projectIntervals = locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid]).reduce(
        (acc2, { intervals = [] }) => [...acc2, ...intervals], [])
      projectIntervals.forEach((interval) => {
        if (!acc[interval.chrom]) {
          acc[interval.chrom] = {}
        }
        if (!acc[interval.chrom][projectGuid]) {
          acc[interval.chrom][projectGuid] = []
        }
        acc[interval.chrom][projectGuid].push(interval)
      })
      return acc
    }, {}),
)

export const getLocusListTableData = createSelector(
  (state, props) => props.omitLocusLists,
  getLocusListsWithGenes,
  (omitLocusLists, locusListsByGuid) => {
    let data = Object.values(locusListsByGuid)
    if (omitLocusLists) {
      data = data.filter(locusList => !omitLocusLists.includes(locusList.locusListGuid))
    }

    return data.reduce((acc, locusList) => {
      if (locusList.canEdit) {
        acc.My.push(locusList)
      } else if (locusList.isPublic) {
        acc.Public.push(locusList)
      }
      return acc
    }, { My: [], Public: [] })
  },
)
