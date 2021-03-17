import { createSelector } from 'reselect'
import orderBy from 'lodash/orderBy'
import uniqBy from 'lodash/uniqBy'

import { compareObjects } from 'shared/utils/sortUtils'
import { NOTE_TAG_NAME, familyVariantSamples } from 'shared/utils/constants'

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

/**
 * function that returns a mapping of each familyGuid to an array of individuals in that family.
 * The array of individuals is in sorted order.
 *
 * @param state {object} global Redux state
 */
export const getSortedIndividualsByFamily = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getMmeSubmissionsByGuid,
  (familiesByGuid, individualsByGuid, mmeSubmissionsByGuid) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivAffectedSort = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0
    const getIndivMmeSort = ({ mmeSubmissionGuid }) => {
      const { deletedDate, createdDate = '1900-01-01' } = mmeSubmissionsByGuid[mmeSubmissionGuid] || {}
      return deletedDate ? '2000-01-01' : createdDate
    }

    return Object.entries(familiesByGuid).reduce((acc, [familyGuid, family]) => ({
      ...acc,
      [familyGuid]: orderBy(
        (family.individualGuids || []).map(individualGuid => individualsByGuid[individualGuid]),
        [getIndivAffectedSort, getIndivMmeSort], ['asc', 'desc'],
      ),
    }), {})
  },
)

export const getFirstSampleByFamily = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getSamplesByGuid,
  (familiesByGuid, individualsByGuid, samplesByGuid) => {
    return Object.entries(familiesByGuid).reduce((acc, [familyGuid, family]) => {
      const familySamples = familyVariantSamples(family, individualsByGuid, samplesByGuid)

      return {
        ...acc,
        [familyGuid]: familySamples.length > 0 ? familySamples[0] : null,
      }
    }, {})
  },
)

export const getHasActiveVariantSampleByFamily = createSelector(
  getSortedIndividualsByFamily,
  getSamplesByGuid,
  (individualsByFamily, samplesByGuid) => {
    return Object.entries(individualsByFamily).reduce((acc, [familyGuid, individuals]) => ({
      ...acc,
      [familyGuid]: individuals.some(individual => (individual.sampleGuids || []).some(
        sampleGuid => samplesByGuid[sampleGuid].isActive,
      )),
    }), {})
  },
)

export const getIGVSamplesByFamilySampleIndividual = createSelector(
  getSortedIndividualsByFamily,
  getIgvSamplesByGuid,
  (individualsByFamily, igvSamplesByGuid) => {
    return Object.entries(individualsByFamily).reduce((acc, [familyGuid, individuals]) => ({
      ...acc,
      [familyGuid]: individuals.reduce((familyAcc, { individualGuid, igvSampleGuids }) => {
        (igvSampleGuids || []).forEach((sampleGuid) => {
          const sample = igvSamplesByGuid[sampleGuid]
          const type = sample.sampleType
          if (!familyAcc[type]) {
            familyAcc[type] = {}
          }
          familyAcc[type][individualGuid] = sample
        })
        return familyAcc
      }, {}),
    }), {})
  },
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

export const getParsedLocusList = createSelector(
  getLocusListsByGuid,
  getGenesById,
  (state, props) => props.locusListGuid,
  (locusListsByGuid, genesById, locusListGuid) => {
    const locusList = locusListsByGuid[locusListGuid] || {}
    if (locusList.items) {
      locusList.items = locusList.items.map((item) => {
        const gene = genesById[item.geneId]
        let display
        if (item.geneId) {
          display = gene ? gene.geneSymbol : item.geneId
        } else {
          display = `chr${item.chrom}:${item.start}-${item.end}`
        }
        return { ...item, display, gene }
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
