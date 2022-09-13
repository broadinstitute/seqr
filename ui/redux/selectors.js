import { createSelector } from 'reselect'
import uniqBy from 'lodash/uniqBy'

import { compHetGene } from 'shared/components/panel/variants/VariantUtils'
import { compareObjects } from 'shared/utils/sortUtils'
import { NOTE_TAG_NAME } from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getFamiliesByGuid = state => state.familiesByGuid
export const getFamilyNotesByGuid = state => state.familyNotesByGuid
export const getFamilyDetailsLoading = state => state.familyDetailsLoading
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getIgvSamplesByGuid = state => state.igvSamplesByGuid
export const getAnalysisGroupsByGuid = state => state.analysisGroupsByGuid
export const getAnalysisGroupIsLoading = state => state.analysisGroupsLoading.isLoading
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
export const getRnaSeqDataByIndividual = state => state.rnaSeqDataByIndividual
export const getUser = state => state.user
export const getUserOptionsByUsername = state => state.userOptionsByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getVersion = state => state.meta.version
export const getGoogleLoginEnabled = state => state.meta.googleLoginEnabled
export const getHijakEnabled = state => state.meta.hijakEnabled
export const getWarningMessages = state => state.meta.warningMessages
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

const groupByFamilyGuid = objs => objs.reduce((acc, o) => {
  if (!acc[o.familyGuid]) {
    acc[o.familyGuid] = []
  }
  acc[o.familyGuid].push(o)
  return acc
}, {})

export const getNotesByFamilyType = createSelector(
  getFamilyNotesByGuid,
  notesByGuid => Object.values(notesByGuid).reduce((acc, note) => {
    if (!acc[note.familyGuid]) {
      acc[note.familyGuid] = {}
    }
    if (!acc[note.familyGuid][note.noteType]) {
      acc[note.familyGuid][note.noteType] = []
    }
    acc[note.familyGuid][note.noteType].push(note)
    return acc
  }, {}),
)

export const getProjectAnalysisGroupOptions = createSelector(
  getAnalysisGroupsGroupedByProjectGuid,
  analysisGroupsByProject => Object.entries(analysisGroupsByProject).reduce(
    (acc, [projectGuid, analysisGroupsByGuid]) => ({
      ...acc,
      [projectGuid]: Object.values(analysisGroupsByGuid).sort((a, b) => a.name.localeCompare(b.name)),
    }), {},
  ),
)

export const getAnalysisGroupsByFamily = createSelector(
  getAnalysisGroupsByGuid,
  analysisGroupsByGuid => Object.values(analysisGroupsByGuid).reduce(
    (acc, analysisGroup) => analysisGroup.familyGuids.reduce(
      (familyAcc, familyGuid) => ({ ...familyAcc, [familyGuid]: [...(familyAcc[familyGuid] || []), analysisGroup] }),
      acc,
    ), {},
  ),
)

export const getIndividualsByFamily = createSelector(
  getIndividualsByGuid,
  individualsByGuid => groupByFamilyGuid(Object.values(individualsByGuid)),
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
  groupByFamilyGuid,
)

const getSortedSamples = createSelector(
  getSamplesByGuid,
  samplesByGuid => Object.values(samplesByGuid).sort((a, b) => a.loadedDate.localeCompare(b.loadedDate)),
)

export const getSamplesByFamily = createSelector(
  getSortedSamples,
  sortedSamples => groupByFamilyGuid(sortedSamples || []),
)

export const getHasActiveSearchableSampleByFamily = createSelector(
  getSamplesByFamily,
  samplesByFamily => Object.entries(samplesByFamily).reduce(
    (acc, [familyGuid, familySamples]) => ({
      ...acc,
      [familyGuid]: {
        isActive: familySamples.some(({ isActive }) => isActive),
        isSearchable: familySamples.some(({ isActive, elasticsearchIndex }) => isActive && elasticsearchIndex),
      },
    }), {},
  ),
)

export const getIGVSamplesByFamilySampleIndividual = createSelector(
  getIgvSamplesByGuid,
  igvSamplesByGuid => Object.values(igvSamplesByGuid).reduce((acc, sample) => {
    if (!acc[sample.familyGuid]) {
      acc[sample.familyGuid] = {}
    }
    if (!acc[sample.familyGuid][sample.sampleType]) {
      acc[sample.familyGuid][sample.sampleType] = {}
    }
    acc[sample.familyGuid][sample.sampleType][sample.individualGuid] = sample
    return acc
  }, {}),
)

export const getProjectDatasetTypes = createSelector(
  getProjectsByGuid,
  getSamplesGroupedByProjectGuid,
  (projectsByGuid, samplesByProjectGuid) => Object.values(projectsByGuid).reduce(
    (acc, { projectGuid, datasetTypes }) => ({
      ...acc,
      [projectGuid]: datasetTypes || [...new Set(Object.values(samplesByProjectGuid[projectGuid] || {}).filter(
        ({ isActive, elasticsearchIndex }) => isActive && elasticsearchIndex,
      ).map(({ datasetType }) => datasetType))],
    }), {},
  ),
)

// Saved variant selectors
export const getVariantId = variant => (
  Array.isArray(variant) ? variant : [variant]).map(({ variantId }) => variantId).sort().join(',')

const groupByVariantGuidFields = (variantTagNotes, objectsByGuid, savedVariantsByGuid, field) => Object.values(
  objectsByGuid,
).forEach((o) => {
  const variantGuids = o.variantGuids.sort().join(',')
  if (!variantTagNotes[variantGuids]) {
    variantTagNotes[variantGuids] = { // eslint-disable-line no-param-reassign
      variantGuids, variants: o.variantGuids.map(variantGuid => savedVariantsByGuid[variantGuid]),
    }
  }
  if (!variantTagNotes[variantGuids][field]) {
    variantTagNotes[variantGuids][field] = [] // eslint-disable-line no-param-reassign
  }
  variantTagNotes[variantGuids][field].push(o)
})

export const getVariantTagNotesByFamilyVariants = createSelector(
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  getVariantFunctionalDataByGuid,
  getSavedVariantsByGuid,
  (tagsByGuids, notesByGuids, functionalDataByGuids, savedVariantsByGuid) => {
    const variantTagNotes = {}
    groupByVariantGuidFields(variantTagNotes, tagsByGuids, savedVariantsByGuid, 'tags')
    groupByVariantGuidFields(variantTagNotes, notesByGuids, savedVariantsByGuid, 'notes')
    groupByVariantGuidFields(variantTagNotes, functionalDataByGuids, savedVariantsByGuid, 'functionalData')

    Object.values(savedVariantsByGuid).forEach((variant) => {
      if (!variantTagNotes[variant.variantGuid]) {
        variantTagNotes[variant.variantGuid] = { variantGuids: variant.variantGuid, variants: [variant] }
      }
    })

    return Object.values(variantTagNotes).reduce((acc, { variants, ...variantDetail }) => {
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

export const getLocusListsWithGenes = createSelector(
  getLocusListsByGuid,
  getGenesById,
  (locusListsByGuid, genesById) => Object.entries(locusListsByGuid).reduce(
    (acc, [locusListGuid, locusList]) => ({
      ...acc,
      [locusListGuid]: {
        ...locusList,
        items:
          locusList.items &&
          locusList.items.map(item => ({ ...item, gene: genesById[item.geneId], pagene: item.pagene })),
      },
    }), {},
  ),
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
  (flattenCompoundHet, searchedVariants) => {
    const shouldFlatten = Object.values(flattenCompoundHet || {}).some(val => val)
    if (!shouldFlatten) {
      return searchedVariants || []
    }
    const flattened = flattenCompoundHet.all ? searchedVariants.flat() : searchedVariants.reduce((acc, variant) => (
      (Array.isArray(variant) && flattenCompoundHet[compHetGene(variant)]) ? [...acc, ...variant] : [...acc, variant]
    ), [])
    return uniqBy(flattened, 'variantId')
  },
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

export const getLocusListIntervalsByChromProject = createSelector(
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectsByGuid, locusListsByGuid) => Object.entries(projectsByGuid).reduce(
    (acc, [projectGuid, { locusListGuids = [] }]) => {
      const projectIntervals = locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid]).reduce(
        (acc2, { intervals = [] }) => [...acc2, ...intervals], [],
      )
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
    }, {},
  ),
)

export const getLocusListTableData = createSelector(
  (state, props) => props.meta && props.meta.data && props.meta.data.formId,
  getProjectsByGuid,
  getLocusListsWithGenes,
  (omitProjectGuid, projectsByGuid, locusListsByGuid) => {
    let data = Object.values(locusListsByGuid)
    if (omitProjectGuid) {
      const { locusListGuids = [] } = projectsByGuid[omitProjectGuid] || {}
      data = data.filter(locusList => !locusListGuids.includes(locusList.locusListGuid))
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

export const getUserOptions = createSelector(
  getUserOptionsByUsername,
  usersOptionsByUsername => Object.values(usersOptionsByUsername).map(
    user => ({ key: user.username, value: user.username, text: user.displayName ? `${user.displayName} (${user.email})` : user.email }),
  ),
)
