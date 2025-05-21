import { createSelector } from 'reselect'

import { compareObjects } from 'shared/utils/sortUtils'
import { NOTE_TAG_NAME, MME_TAG_NAME, FAMILY_FIELD_ANALYSED_BY, CATEGORY_FAMILY_FILTERS } from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
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
export const getTranscriptsById = state => state.transcriptsById
export const getTotalSampleCounts = state => state.totalSampleCounts
export const getHpoTermsByParent = state => state.hpoTermsByParent
export const getHpoTermsIsLoading = state => state.hpoTermsLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getRnaSeqDataByIndividual = state => state.rnaSeqDataByIndividual
export const getPhenotypeGeneScoresByIndividual = state => state.phenotypeGeneScoresByIndividual
export const getUser = state => state.user
export const getUserOptionsByUsername = state => state.userOptionsByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getVersion = state => state.meta.version
export const getOauthLoginEnabled = state => !!state.meta.oauthLoginProvider
export const getOauthLoginProvider = state => state.meta.oauthLoginProvider
export const getElasticsearchEnabled = state => state.meta.elasticsearchEnabled
export const getVlmEnabled = state => state.meta.vlmEnabled
export const getHijakEnabled = state => state.meta.hijakEnabled
export const getWarningMessages = state => state.meta.warningMessages
export const getAnvilLoadingDelayDate = state => state.meta.anvilLoadingDelayDate
export const getSavedVariantsIsLoading = state => state.savedVariantsLoading.isLoading
export const getSavedVariantsLoadingError = state => state.savedVariantsLoading.errorMessage
export const getSearchesByHash = state => state.searchesByHash
export const getSearchFamiliesByHash = state => state.searchFamiliesByHash

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
    (acc, analysisGroup) => (analysisGroup.familyGuids || []).reduce(
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

export const getHasActiveSearchSampleByFamily = createSelector(
  getSamplesByFamily,
  samplesByFamily => Object.entries(samplesByFamily).reduce(
    (acc, [familyGuid, familySamples]) => ({
      ...acc,
      [familyGuid]: familySamples.some(({ isActive }) => isActive),
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

export const getSelectableTagTypesByProject = createSelector(
  getProjectsByGuid,
  projectsByGuid => Object.values(projectsByGuid).reduce((acc, project) => ({
    ...acc,
    [project.projectGuid]: (project.variantTagTypes || []).filter(
      vtt => vtt.name !== NOTE_TAG_NAME && vtt.name !== MME_TAG_NAME,
    ),
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

const groupDataNestedByChrom = (initialData, groupedData, nestedKey) => groupedData.reduce(
  (acc, data) => {
    const { chrom } = data
    if (!acc[chrom]) {
      acc[chrom] = {}
    }
    if (!acc[chrom][nestedKey]) {
      acc[chrom][nestedKey] = []
    }
    acc[chrom][nestedKey].push(data)
    return acc
  }, initialData,
)

export const getOmimIntervalsByChrom = createSelector(
  state => state.omimIntervals,
  omimIntervals => groupDataNestedByChrom({}, Object.values(omimIntervals || {}), 'omim'),
)

export const getLocusListIntervalsByChromProject = createSelector(
  getProjectsByGuid,
  getLocusListsByGuid,
  (projectsByGuid, locusListsByGuid) => Object.entries(projectsByGuid).reduce(
    (acc, [projectGuid, { locusListGuids = [] }]) => {
      const projectIntervals = locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid]).reduce(
        (acc2, { intervals = [] }) => [...acc2, ...intervals], [],
      )
      return groupDataNestedByChrom(acc, projectIntervals, projectGuid)
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

    data = data.map(({ items, ...locusList }) => (items ?
      { geneNames: items.map(({ gene }) => (gene || {}).geneSymbol), ...locusList } :
      locusList))

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

export const getHpoTermOptionsByFamily = createSelector(
  getIndividualsByFamily,
  individualsByFamily => Object.entries(individualsByFamily).reduce((acc, [familyGuid, individuals]) => ({
    ...acc,
    [familyGuid]: individuals.reduce((fAcc, { features }) => ([...fAcc, ...(features || []).map(
      ({ id, label }) => ({ value: id, text: label, description: id }),
    )]), [{ value: 'Uncertain' }]),
  }), {}),
)

export const getRnaSeqSignificantJunctionData = createSelector(
  getGenesById,
  getIndividualsByGuid,
  getRnaSeqDataByIndividual,
  (genesById, individualsByGuid, rnaSeqDataByIndividual) => Object.entries(rnaSeqDataByIndividual || {}).reduce(
    (acc, [individualGuid, rnaSeqData]) => {
      const individualData = Object.values(rnaSeqData.spliceOutliers || {}).flat()
        .filter(({ isSignificant }) => isSignificant)
        .sort((a, b) => a.pValue - b.pValue)
        .map(({ geneId, chrom, start, end, strand, type, ...cols }) => ({
          geneSymbol: (genesById[geneId] || {}).geneSymbol || geneId,
          idField: `${geneId}-${chrom}-${start}-${end}-${strand}-${type}`,
          familyGuid: individualsByGuid[individualGuid].familyGuid,
          individualName: individualsByGuid[individualGuid].displayName,
          individualGuid,
          ...{ geneId, chrom, start, end, strand, type, ...cols },
        }))
      return (individualData.length > 0 ? { ...acc, [individualGuid]: individualData } : acc)
    }, {},
  ),
)

export const getSpliceOutliersByChromFamily = createSelector(
  getRnaSeqSignificantJunctionData,
  spliceDataByIndiv => Object.values(spliceDataByIndiv).reduce(
    (acc, spliceData) => (groupDataNestedByChrom(acc, spliceData, spliceData[0].familyGuid)), {},
  ),
)

const ANALYSED_BY_FILTER_LOOKUP = Object.values(CATEGORY_FAMILY_FILTERS).reduce(
  (acc, options) => {
    options.forEach((opt) => {
      acc[opt.value] = opt.analysedByFilter
    })
    return acc
  }, {},
)

const NO_ANALYSED_BY_FIELDS = Object.values(CATEGORY_FAMILY_FILTERS).reduce(
  (acc, options) => {
    options.filter(opt => opt.requireNoAnalysedBy).forEach((opt) => {
      acc.add(opt.value)
    })
    return acc
  }, new Set(),
)

const ANALYSED_BY_CATEGORY_OPTION_LOOKUP = CATEGORY_FAMILY_FILTERS[FAMILY_FIELD_ANALYSED_BY].reduce(
  (acc, { value, category }) => ({ ...acc, [value]: category || 'Analysed By' }), {},
)

const isAnalysedBy = (family, analysedByFilter, user, analysedByOptions) => {
  let requireNoAnalysedBy = false
  const analsedByGroups = Object.values(analysedByFilter.reduce(
    (acc, val) => {
      const optFilter = analysedByOptions?.has(val) ? ({ createdBy }) => createdBy === val :
        ANALYSED_BY_FILTER_LOOKUP[val]
      if (optFilter) {
        const category = ANALYSED_BY_CATEGORY_OPTION_LOOKUP[val]
        if (!acc[category]) {
          acc[category] = []
        }
        acc[category].push(optFilter)
      }
      if (NO_ANALYSED_BY_FIELDS.has(val)) {
        requireNoAnalysedBy = true
      }
      return acc
    }, {},
  ))
  if (!analsedByGroups.length) {
    return true
  }
  const filteredAnalysedBy = analsedByGroups.reduce(
    (acc, filterGroup) => acc.filter(analysedBy => filterGroup.some(f => f(analysedBy, user))),
    family.analysedBy,
  )
  return requireNoAnalysedBy ? filteredAnalysedBy.length === 0 : filteredAnalysedBy.length > 0
}

export const familyPassesFilters = createSelector(
  getUser,
  getSamplesByFamily,
  (user, samplesByFamily) => (
    family, groupedFilters, analysedByOptions, categoryFilters = CATEGORY_FAMILY_FILTERS,
  ) => {
    if (groupedFilters.analysedBy && !isAnalysedBy(family, groupedFilters.analysedBy, user, analysedByOptions)) {
      return false
    }
    return Object.entries(groupedFilters).every(([key, groupVals]) => {
      const filters = categoryFilters[key]?.filter(
        opt => groupVals.includes(opt.value) && opt.createFilter,
      ).map(opt => opt.createFilter)
      return !filters?.length || filters.some(filter => filter(family, user, samplesByFamily))
    })
  },
)

export const getProjectAnalysisGroupFamilyGuidsByGuid = createSelector(
  getAnalysisGroupsGroupedByProjectGuid,
  getFamiliesGroupedByProjectGuid,
  familyPassesFilters,
  (state, props) => (
    state.currentProjectGuid ||
    props.projectGuid ||
    props.value?.projectGuid ||
    props.match?.params?.projectGuid ||
    props.match?.params?.entityGuid
  ),
  (projectAnalysisGroupsByGuid, familiesByProjectGuid, passesFilterFunc, projectGuid) => (
    [
      ...Object.values(projectAnalysisGroupsByGuid[projectGuid] || {}),
      ...Object.values(projectAnalysisGroupsByGuid.null || {}),
    ].reduce((acc, analysisGroup) => ({
      ...acc,
      [analysisGroup.analysisGroupGuid]: analysisGroup.criteria ?
        Object.values(familiesByProjectGuid[projectGuid] || {}).filter(
          family => passesFilterFunc(family, analysisGroup.criteria),
        ).map(family => family.familyGuid) : analysisGroup.familyGuids,
    }), {})
  ),
)

export const getAnalysisGroupGuid = (state, props) => (
  (props || {}).match ? props.match.params.analysisGroupGuid : (props || {}).analysisGroupGuid
)

export const getCurrentAnalysisGroupFamilyGuids = createSelector(
  getAnalysisGroupGuid,
  getProjectAnalysisGroupFamilyGuidsByGuid,
  (state, props) => state.currentProjectGuid || props.match?.params?.projectGuid,
  (analysisGroupGuid, analysisGroupFamilyGuidsByGuid) => analysisGroupFamilyGuidsByGuid[analysisGroupGuid],
)
