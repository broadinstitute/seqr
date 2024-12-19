import { createSelector } from 'reselect'

import {
  ALL_FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_NOTES_FIELDS,
  getVariantSummary,
  INDIVIDUAL_EXPORT_DATA,
  INDIVIDUAL_HAS_DATA_FIELD,
  MME_TAG_NAME,
  TISSUE_DISPLAY,
  SIMPLIFIED_SEX_LOOKUP,
} from 'shared/utils/constants'
import { toCamelcase, toSnakecase, snakecaseToTitlecase } from 'shared/utils/stringUtils'

import {
  getProjectsByGuid, getFamiliesGroupedByProjectGuid, getIndividualsByGuid, getSamplesByGuid, getGenesById, getUser,
  getAnalysisGroupsGroupedByProjectGuid, getSavedVariantsByGuid, getSortedIndividualsByFamily,
  getMmeResultsByGuid, getMmeSubmissionsByGuid, getHasActiveSearchSampleByFamily, getSelectableTagTypesByProject,
  getVariantTagsByGuid, getUserOptionsByUsername, getSamplesByFamily, getNotesByFamilyType,
  getVariantTagNotesByFamilyVariants, getPhenotypeGeneScoresByIndividual,
  getRnaSeqDataByIndividual, familyPassesFilters, getAnalysisGroupGuid, getCurrentAnalysisGroupFamilyGuids,
} from 'redux/selectors'

import {
  SORT_BY_FAMILY_NAME,
  CASE_REVIEW_STATUS_OPTIONS,
  CASE_REVIEW_FILTER_LOOKUP,
  FAMILY_SORT_OPTIONS,
  FAMILY_EXPORT_DATA,
  CASE_REVIEW_FAMILY_EXPORT_DATA,
  CASE_REVIEW_TABLE_NAME,
  CASE_REVIEW_INDIVIDUAL_EXPORT_DATA,
  SAMPLE_EXPORT_DATA,
  PROJECT_CATEGORY_FAMILY_FILTERS,
} from './constants'

const FAMILY_SORT_LOOKUP = FAMILY_SORT_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.createSortKeyGetter,
  }), {},
)

// project data selectors

export const getProjectGuid = state => state.currentProjectGuid
export const getProjectOverviewIsLoading = state => state.projectOverviewLoading.isLoading
export const getProjectCollaboratorsIsLoading = state => state.projectCollaboratorsLoading.isLoading
export const getProjectLocusListsIsLoading = state => state.projectLocusListsLoading.isLoading
export const getMatchmakerMatchesLoading = state => state.matchmakerMatchesLoading.isLoading
export const getMatchmakerContactNotes = state => state.mmeContactNotes
export const getRnaSeqDataLoading = state => state.rnaSeqDataLoading.isLoading
export const getPhenotypeDataLoading = state => state.phenotypeDataLoading.isLoading
export const getFamiliesLoading = state => state.familiesLoading.isLoading
export const getFamilyVariantSummaryLoading = state => state.familyVariantSummaryLoading.isLoading
export const getIndivdualsLoading = state => state.individualsLoading.isLoading
export const getMmeSubmissionsLoading = state => state.mmeSubmissionsLoading.isLoading
export const getSamplesLoading = state => state.samplesLoading.isLoading
export const getTagTypesLoading = state => state.tagTypesLoading.isLoading
export const getFamilyTagTypeCounts = state => state.familyTagTypeCounts
export const getSavedVariantTableState = state => state.savedVariantTableState
export const getGregorMetadataImportStats = state => state.importStats.gregorMetadata
const getFamiliesTableFiltersByProject = state => state.familyTableFilterState

export const getCurrentProject = createSelector(
  getProjectsByGuid, getProjectGuid, (projectsByGuid, currentProjectGuid) => projectsByGuid[currentProjectGuid],
)

const selectEntitiesForProjectGuid =
  (entitiesGroupedByProjectGuid, projectGuid) => entitiesGroupedByProjectGuid[projectGuid] || {}
export const getProjectFamiliesByGuid = createSelector(
  getFamiliesGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid,
)
export const getProjectAnalysisGroupsByGuid = createSelector(
  getAnalysisGroupsGroupedByProjectGuid,
  getProjectGuid,
  (groupedAnalysisGroups, projectGuid) => ({
    ...selectEntitiesForProjectGuid(groupedAnalysisGroups, projectGuid),
    ...selectEntitiesForProjectGuid(groupedAnalysisGroups, null),
  }),
)

export const getProjectAnalysisGroupFamiliesByGuid = createSelector(
  getProjectFamiliesByGuid,
  getCurrentAnalysisGroupFamilyGuids,
  (projectFamiliesByGuid, analysisGroupFamilyGuids) => {
    if (!analysisGroupFamilyGuids) {
      return projectFamiliesByGuid
    }
    return analysisGroupFamilyGuids.reduce(
      (acc, familyGuid) => ({ ...acc, [familyGuid]: projectFamiliesByGuid[familyGuid] }), {},
    )
  },
)

const getFamilySizeHistogram = familyCounts => familyCounts.reduce((acc, { size, parents }) => {
  const parentCounts = Object.values(parents.reduce(
    (parentAcc, { maternalGuid, paternalGuid }) => {
      const parentKey = `${maternalGuid || ''}-${paternalGuid || ''}`
      const parent = parentAcc[parentKey] || {
        numParents: [maternalGuid, paternalGuid].filter(g => g).length,
        numChildren: 0,
      }
      parent.numChildren += 1
      return { ...parentAcc, [parentKey]: parent }
    }, {},
  ))
  const sizeAcc = acc[size] || { total: 0, withParents: 0, trioPlus: 0, quadPlus: 0 }
  sizeAcc.total += 1
  const mainParentCount = parentCounts.find(({ numParents }) => numParents === (size === 2 ? 1 : 2))
  const mainFamilySize = mainParentCount ? mainParentCount.numChildren + mainParentCount.numParents : 0
  if (mainFamilySize === size) {
    sizeAcc.withParents += 1
  } else if (mainFamilySize === 3) {
    sizeAcc.trioPlus += 1
  } else if (mainFamilySize > 3) {
    sizeAcc.quadPlus += 1
  }
  return { ...acc, [size]: sizeAcc }
}, {})

export const getProjectAnalysisGroupFamilySizeHistogram = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  familiesByGuid => getFamilySizeHistogram(Object.values(familiesByGuid).map(family => ({
    size: (family.individualGuids || []).length,
    parents: family.parents || [],
  }))),
)

export const getProjectAnalysisGroupDataLoadedFamilySizeHistogram = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  getSamplesByFamily,
  (familiesByGuid, samplesByFamily) => getFamilySizeHistogram(Object.values(familiesByGuid).map(((family) => {
    const sampleIndividuals = new Set((samplesByFamily[family.familyGuid] || []).filter(
      sample => sample.isActive,
    ).map(sample => sample.individualGuid))
    const hasSampleParents = (family.parents || []).reduce(
      (acc, { individualGuid, maternalGuid, paternalGuid }) => {
        const hasSampleMaternal = sampleIndividuals.has(maternalGuid)
        const hasSamplePaternal = sampleIndividuals.has(paternalGuid)
        if (sampleIndividuals.has(individualGuid) && (hasSampleMaternal || hasSamplePaternal)) {
          acc.push({
            maternalGuid: hasSampleMaternal ? maternalGuid : null,
            paternalGuid: hasSamplePaternal ? paternalGuid : null,
          })
        }
        return acc
      }, [],
    )
    return {
      size: sampleIndividuals.size,
      parents: hasSampleParents,
    }
  })).filter(({ size }) => size > 0)),
)

export const getProjectAnalysisGroupIndividualsByGuid = createSelector(
  getIndividualsByGuid,
  getProjectAnalysisGroupFamiliesByGuid,
  (individualsByGuid, familiesByGuid) => Object.values(familiesByGuid).reduce((acc, family) => ({
    ...acc,
    ...family.individualGuids.reduce((indivAcc, individualGuid) => (
      { ...indivAcc, [individualGuid]: { ...individualsByGuid[individualGuid], [FAMILY_FIELD_ID]: family.familyId } }
    ), {}),
  }), {}),
)

export const getProjectAnalysisGroupSamplesByTypes = createSelector(
  getCurrentProject,
  getCurrentAnalysisGroupFamilyGuids,
  (project, analysisGroupFamilyGuids) => Object.entries(project.sampleCounts || {}).map(
    ([key, typeCounts]) => ([key, typeCounts.map(({ familyCounts, ...data }) => ({
      ...data,
      count: Object.entries(familyCounts).reduce((total, [familyGuid, count]) => (
        (!analysisGroupFamilyGuids || analysisGroupFamilyGuids.includes(familyGuid)) ? total + count : total
      ), 0),
    })).filter(({ count }) => count > 0)]),
  ),
)

export const getProjectAnalysisGroupMmeSubmissionDetails = createSelector(
  getMmeSubmissionsByGuid,
  getProjectAnalysisGroupFamiliesByGuid,
  getGenesById,
  getNotesByFamilyType,
  (submissionsByGuid, familiesByGuid, genesById, notesByFamilyType) => {
    const individualFamilies = Object.values(familiesByGuid).reduce((acc, family) => ({
      ...acc,
      ...family.individualGuids.reduce((acc2, individualGuid) => ({ ...acc2, [individualGuid]: family }), {}),
    }), {})

    return Object.values(submissionsByGuid).reduce((acc, submission) => {
      const family = individualFamilies[submission.individualGuid]
      return family ? [...acc, {
        mmeNotes: (notesByFamilyType[family.familyGuid] || {}).M,
        familyName: family.displayName,
        familyGuid: family.familyGuid,
        projectGuid: family.projectGuid,
        geneSymbols: (submission.geneIds || []).map(geneId => (genesById[geneId] || {}).geneSymbol || geneId),
        ...submission,
      }] : acc
    }, [])
  },
)

export const getTaggedVariantsByFamily = createSelector(
  getSavedVariantsByGuid,
  getGenesById,
  getVariantTagsByGuid,
  (savedVariants, genesById, variantTagsByGuid) => Object.values(savedVariants).filter(
    variant => variant.tagGuids.length,
  ).reduce((acc, variant) => {
    const { familyGuids, ...variantDetail } = variant
    variantDetail.tags = variant.tagGuids.map(tagGuid => variantTagsByGuid[tagGuid])
    variantDetail.genes = Object.keys(variant.transcripts || {}).map(geneId => genesById[geneId])
    familyGuids.forEach((familyGuid) => {
      if (!acc[familyGuid]) {
        acc[familyGuid] = []
      }
      acc[familyGuid].push(variantDetail)
    })
    return acc
  }, {}),
)

export const getTaggedVariantsByFamilyType = createSelector(
  getTaggedVariantsByFamily,
  variantsByFamily => Object.entries(variantsByFamily).reduce((acc, [familyGuid, variants]) => ({
    ...acc,
    [familyGuid]: variants.reduce((acc2, variant) => {
      const isSv = !!variant.svType
      const accSvVals = acc2[isSv] || []
      accSvVals.push(variant)
      return { ...acc2, [isSv]: accSvVals }
    }, {}),
  }), {}),
)

export const getSavedVariantTagTypeCountsByFamily = createSelector(
  getTaggedVariantsByFamily,
  variantsByFamily => Object.entries(variantsByFamily).reduce(
    (acc, [familyGuid, variants]) => ({
      ...acc,
      [familyGuid]: variants.reduce((acc2, { tags, mmeSubmissions = [] }) => {
        const counts = {}
        if (mmeSubmissions.length) {
          counts[MME_TAG_NAME] = (acc2[MME_TAG_NAME] || 0) + 1
        }
        tags.forEach(({ name }) => {
          if (!counts[name]) {
            counts[name] = acc2[name] || 0
          }
          counts[name] += 1
        })
        return { ...acc2, ...counts }
      }, {}),
    }), {},
  ),
)

export const getSavedVariantTagTypeCounts = createSelector(
  getVariantTagsByGuid,
  getSavedVariantsByGuid,
  (variantTagsByGuid, savedVariantsByGuid) => Object.values(variantTagsByGuid).reduce(
    (acc, { name }) => ({ ...acc, [name]: (acc[name] || 0) + 1 }), {
      [MME_TAG_NAME]: Object.values(savedVariantsByGuid).filter(
        ({ mmeSubmissions = [] }) => mmeSubmissions.length > 0,
      ).length,
    },
  ),
)

export const getAnalysisGroupTagTypeCounts = createSelector(
  getCurrentAnalysisGroupFamilyGuids,
  getFamilyTagTypeCounts,
  (analysisGroupFamilyGuids, familyTagTypeCounts) => (analysisGroupFamilyGuids ? analysisGroupFamilyGuids.reduce(
    (acc, familyGuid) => Object.entries(familyTagTypeCounts[familyGuid] || {}).reduce((acc2, [tagType, count]) => (
      { ...acc2, [tagType]: count + (acc2[tagType] || 0) }
    ), acc), {},
  ) : {}),
)

export const getTagTypeCounts = createSelector(
  getCurrentProject,
  project => project?.variantTagTypes?.reduce((acc, { name, numTags }) => ({ ...acc, [name]: numTags }), {}),
)

export const getVariantGeneId = ({ variantGuid, geneId }, variantGeneId) => `${variantGuid}-${variantGeneId || geneId}`

export const getIndividualTaggedVariants = createSelector(
  getTaggedVariantsByFamily,
  getIndividualsByGuid,
  (state, props) => props.individualGuid,
  (taggedVariants, individualsByGuid, individualGuid) => {
    const { familyGuid } = individualsByGuid[individualGuid]
    return Object.values(taggedVariants[familyGuid] || []).reduce((acc, variant) => {
      const variantDetail = {
        ...variant.genotypes[individualGuid],
        ...variant,
      }
      return [...acc, ...variant.genes.filter(gene => gene).map(gene => ({
        ...variantDetail,
        variantId: getVariantGeneId(variant, gene.geneId),
        ...gene,
      }))]
    }, [])
  },
)

export const getProjectTagTypeOptions = createSelector(
  getProjectGuid,
  getSelectableTagTypesByProject,
  (projectGuid, tagTypesByProject) => tagTypesByProject[projectGuid].map(
    ({ name, variantTagTypeGuid, ...tag }) => ({ value: name, text: name, ...tag }),
  ),
)

export const getProjectVariantSavedByOptions = createSelector(
  getProjectFamiliesByGuid,
  getVariantTagNotesByFamilyVariants,
  (familiesByGuid, variantDetailByFamilyVariant) => [
    { value: null, text: 'View All' },
    ...[...Object.keys(familiesByGuid).reduce(
      (acc, familyGuid) => new Set([
        ...acc,
        ...Object.values(variantDetailByFamilyVariant[familyGuid] || {}).reduce((variantAcc, { tags, notes }) => ([
          ...variantAcc,
          ...(tags || []).map(({ createdBy }) => createdBy),
          ...(notes || []).map(({ createdBy }) => createdBy),
        ]), []),
      ]), new Set(),
    )].map(value => ({ value })),
  ],
)

// Family table selectors
export const getFamiliesTableState = createSelector(
  (state, ownProps) => state[`${toCamelcase((ownProps || {}).tableName) || 'family'}TableState`],
  tableState => tableState,
)

const getFamiliesSearch = createSelector(
  getFamiliesTableState,
  familyTableState => (familyTableState.familiesSearch || '').toLowerCase(),
)
export const getFamiliesSortOrder = createSelector(
  getFamiliesTableState,
  familyTableState => familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME,
)
export const getFamiliesSortDirection = createSelector(
  getFamiliesTableState,
  familyTableState => familyTableState.familiesSortDirection || 1,
)

const hasFamilySearch = createSelector(
  getFamiliesSearch,
  familiesSearch => !!familiesSearch,
)

const getFamilySearchFields = family => ([
  family.displayName, family.familyId, (family.assignedAnalyst || {}).fullName, (family.assignedAnalyst || {}).email,
  ...family.analysedBy.map(({ createdBy }) => createdBy),
])

const getFamiliesBySearchString = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  hasFamilySearch,
  (familiesByGuid, shouldSearch) => {
    if (!shouldSearch) {
      return null
    }

    return Object.values(familiesByGuid).reduce((acc, family) => (
      { ...acc, [getFamilySearchFields(family).join(';').toLowerCase()]: family }), {})
  },
)

const getFamilyAnalysers = createSelector(
  getProjectFamiliesByGuid,
  familiesByGuid => new Set(Object.values(familiesByGuid).reduce(
    (acc, family) => ([...acc, ...(family.analysedBy || []).map(({ createdBy }) => createdBy)]), [],
  )),
)

export const getFamiliesFilterOptionsByCategory = createSelector(
  getFamilyAnalysers,
  analysedByOptions => ({
    ...PROJECT_CATEGORY_FAMILY_FILTERS,
    [FAMILY_FIELD_ANALYSED_BY]: [
      ...PROJECT_CATEGORY_FAMILY_FILTERS[FAMILY_FIELD_ANALYSED_BY],
      ...[...analysedByOptions].map(analysedBy => ({ value: analysedBy, category: 'Analysed By' })),
    ],
  }),
)

export const getFamiliesTableFilters = createSelector(
  getFamiliesTableFiltersByProject,
  getProjectGuid,
  (familyTableFiltersByProject, projectGuid) => (familyTableFiltersByProject || {})[projectGuid],
)

const familyPassesTableFilters = createSelector(
  (state, ownProps) => ownProps?.tableName === CASE_REVIEW_TABLE_NAME,
  state => state.caseReviewTableState.familiesFilter,
  getFamiliesTableFilters,
  getFamilyAnalysers,
  getUser,
  getFamilyTagTypeCounts,
  familyPassesFilters,
  (
    isCaseReview, caseReviewFilter, familyTableFilters, analysedByOptions, user, familyTagTypeCounts, passesFilterFunc,
  ) => (family) => {
    if (isCaseReview) {
      return CASE_REVIEW_FILTER_LOOKUP[caseReviewFilter](family, user)
    }

    const { savedVariants, ...tableFilters } = familyTableFilters || {}
    if (savedVariants?.length && !savedVariants.some(
      tagName => (familyTagTypeCounts[family.familyGuid] || {})[tagName],
    )) {
      return false
    }
    return passesFilterFunc(family, tableFilters, analysedByOptions, PROJECT_CATEGORY_FAMILY_FILTERS)
  },
)

export const getVisibleFamilies = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  getIndividualsByGuid,
  getFamiliesBySearchString,
  getFamiliesSearch,
  familyPassesTableFilters,
  (familiesByGuid, individualsByGuid, familiesBySearchString, familiesSearch, familyFilter) => {
    const searchedFamilies = familiesBySearchString ? Object.keys(familiesBySearchString).filter(
      familySearchString => familySearchString.includes(familiesSearch),
    ).map(familySearchString => familiesBySearchString[familySearchString]) : Object.values(familiesByGuid)
    return familyFilter ?
      searchedFamilies.filter(family => familyFilter({
        ...family,
        individuals: family?.individualGuids?.map(individualGuid => (individualsByGuid[individualGuid])),
      })) : searchedFamilies
  },
)

/**
 * function that returns an array of currently-visible family objects, sorted according to
 * currently-selected values of familiesSortOrder and familiesSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamiliesInSortedOrder = createSelector(
  getVisibleFamilies,
  getIndividualsByGuid,
  getSamplesByFamily,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilies, individualsByGuid, samplesByFamily, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder] ||
      visibleFamilies.some(({ familyId }) => !familyId)) { // families have been loaded without any core fields
      return visibleFamilies
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](individualsByGuid, samplesByFamily)
    return visibleFamilies.slice(0).sort((a, b) => getSortKey(a).localeCompare(getSortKey(b)) * familiesSortDirection)
  },
)

export const getEntityExportConfig = ({ projectName, tableName, fileName, fields }) => ({
  filename: `${projectName.replace(' ', '_').toLowerCase()}_${tableName ? `${toSnakecase(tableName)}_` : ''}${fileName}`,
  headers: fields.map(config => config.header),
  processRow: family => fields.map((config) => {
    const val = family[config.field]
    return config.format ? config.format(val) : val
  }),
})

const getFamiliesExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getSamplesByFamily,
  getNotesByFamilyType,
  (visibleFamilies, samplesByFamily, notesByFamilyType) => visibleFamilies.reduce((acc, family) => [...acc, {
    ...family,
    ...FAMILY_NOTES_FIELDS.reduce((noteAcc, { id, noteType }) => (
      { ...noteAcc, [id]: (notesByFamilyType[family.familyGuid] || {})[noteType] }), {}),
    [FAMILY_FIELD_FIRST_SAMPLE]: (samplesByFamily[family.familyGuid] || [])[0],
  }], []),
)

const getSamplesByIndividual = createSelector(
  getSamplesByGuid,
  samplesByGuid => Object.values(samplesByGuid).reduce((acc, sample) => {
    if (!acc[sample.individualGuid]) {
      acc[sample.individualGuid] = []
    }
    acc[sample.individualGuid].push(sample)
    return acc
  }, {}),
)

const getIndividualsExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getSortedIndividualsByFamily,
  getSamplesByIndividual,
  (families, individualsByFamily, samplesByIndividual) => families.reduce((acc, family) => [
    ...acc, ...(individualsByFamily[family.familyGuid] || []).map(individual => ({
      ...individual,
      [FAMILY_FIELD_ID]: family.familyId,
      [INDIVIDUAL_HAS_DATA_FIELD]: (
        samplesByIndividual[individual.individualGuid] || []).some(({ isActive }) => isActive),
    }))], []),
)

const getSamplesExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getIndividualsByGuid,
  getSamplesByFamily,
  (visibleFamilies, individualsByGuid, samplesByFamily) => visibleFamilies.reduce((acc, family) => [
    ...acc, ...(samplesByFamily[family.familyGuid] || []).map(sample => ({
      ...sample,
      [FAMILY_FIELD_ID]: family.familyId,
      [INDIVIDUAL_FIELD_ID]: individualsByGuid[sample.individualGuid]?.individualId,
    }))], []),
)

export const getProjectExportUrls = createSelector(
  state => getCurrentProject(state).name,
  (state, ownProps) => (ownProps || {}).tableName,
  getAnalysisGroupGuid,
  (projectName, tableName, analysisGroupGuid) => {
    const ownProps = { tableName, analysisGroupGuid }
    const isCaseReview = tableName === CASE_REVIEW_TABLE_NAME
    return [
      {
        name: 'Families',
        getRawData: state => getFamiliesExportData(state, ownProps),
        ...getEntityExportConfig({
          projectName,
          tableName,
          fileName: 'families',
          fields: isCaseReview ? CASE_REVIEW_FAMILY_EXPORT_DATA : FAMILY_EXPORT_DATA,
        }),
      },
      {
        name: 'Individuals',
        getRawData: state => getIndividualsExportData(state, ownProps),
        ...getEntityExportConfig({
          projectName,
          tableName,
          fileName: 'individuals',
          fields: isCaseReview ? CASE_REVIEW_INDIVIDUAL_EXPORT_DATA : INDIVIDUAL_EXPORT_DATA,
        }),
      },
      {
        name: 'Samples',
        getRawData: state => getSamplesExportData(state, ownProps),
        ...getEntityExportConfig({ projectName, tableName, fileName: 'samples', fields: SAMPLE_EXPORT_DATA }),
      },
    ]
  },
)

export const getCaseReviewStatusCounts = createSelector(
  getProjectGuid,
  getIndividualsByGuid,
  (projectGuid, individualsByGuid) => {
    const caseReviewStatusCounts = Object.values(individualsByGuid).reduce((acc, individual) => (
      individual.projectGuid === projectGuid ?
        { ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1 } : acc
    ), {})

    return CASE_REVIEW_STATUS_OPTIONS.map(option => ({ ...option, count: (caseReviewStatusCounts[option.value] || 0) }))
  },
)

export const getAnalysisStatusCounts = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  (familiesByGuid) => {
    const analysisStatusCounts = Object.values(familiesByGuid).reduce((acc, family) => ({
      ...acc, [family.analysisStatus]: (acc[family.analysisStatus] || 0) + 1,
    }), {})

    return ALL_FAMILY_ANALYSIS_STATUS_OPTIONS.map(
      option => ({ ...option, count: (analysisStatusCounts[option.value] || 0) }),
    )
  },
)

export const getDefaultMmeSubmission = createSelector(
  getCurrentProject,
  project => ({
    contactName: project.mmePrimaryDataOwner,
    contactHref: project.mmeContactUrl,
    geneVariants: [],
    phenotypes: [],
  }),
)

export const getMmeResultsBySubmission = createSelector(
  getMmeResultsByGuid,
  getMmeSubmissionsByGuid,
  (mmeResultsByGuid, mmeSubmissionsByGuid) => Object.values(mmeResultsByGuid).reduce((acc, result) => {
    const { submissionGuid } = result
    if (!acc[submissionGuid]) {
      acc[submissionGuid] = { active: [], removed: [] }
    }
    const parsedResult = { ...result.matchStatus, ...result }
    if (parsedResult.matchRemoved || mmeSubmissionsByGuid[submissionGuid].deletedDate) {
      acc[submissionGuid].removed.push(parsedResult)
    } else {
      acc[submissionGuid].active.push(parsedResult)
    }
    return acc
  }, { }),
)

export const getMmeDefaultContactEmail = createSelector(
  getMmeResultsByGuid,
  getMmeSubmissionsByGuid,
  getGenesById,
  getSavedVariantsByGuid,
  getUser,
  (state, ownProps) => ownProps.matchmakerResultGuid,
  (mmeResultsByGuid, mmeSubmissionsByGuid, genesById, savedVariants, user, matchmakerResultGuid) => {
    const { patient, geneVariants, submissionGuid } = mmeResultsByGuid[matchmakerResultGuid]
    const {
      geneVariants: submissionGeneVariants, phenotypes, individualGuid, contactHref, submissionId,
    } = mmeSubmissionsByGuid[submissionGuid]

    const submittedGenes = [...new Set((submissionGeneVariants || []).map(
      ({ geneId }) => (genesById[geneId] || {}).geneSymbol,
    ))]

    const geneName = (geneVariants || []).map(({ geneId }) => (genesById[geneId] || {}).geneSymbol).find(
      geneSymbol => geneSymbol && submittedGenes.includes(geneSymbol),
    )

    const submittedVariants = (submissionGeneVariants || []).map(({ variantGuid }) => (
      getVariantSummary(savedVariants[variantGuid], individualGuid)
    )).join(', ')

    const submittedPhenotypeList = (phenotypes || []).filter(
      ({ observed, label }) => observed === 'yes' && label,
    ).map(({ label }) => label.toLowerCase())
    const numPhenotypes = submittedPhenotypeList.length
    if (numPhenotypes > 2) {
      submittedPhenotypeList[numPhenotypes - 1] = `and ${submittedPhenotypeList[numPhenotypes - 1]}`
    }
    const submittedPhenotypes = submittedPhenotypeList.join(numPhenotypes === 2 ? ' and ' : ', ')

    const contacts = [
      patient.contact.href.replace('mailto:', ''),
      contactHref.replace('mailto:', '').replace('matchmaker@broadinstitute.org,', ''),
      user.email,
    ]
    return {
      matchmakerResultGuid,
      patientId: patient.id,
      to: contacts.filter(val => val).join(','),
      subject: `${geneName || `Patient ${patient.id}`} Matchmaker Exchange connection (${submissionId})`,
      body: `Dear ${patient.contact.name},\n\nWe recently matched with one of your patients in Matchmaker Exchange harboring ${(submissionGeneVariants || []).length === 1 ? 'a variant' : 'variants'} in ${submittedGenes.join(', ')}. Our patient has ${submittedVariants}${submittedPhenotypes ? ` and presents with ${submittedPhenotypes}` : ''}. Would you be willing to share whether your patient's phenotype and genotype match with ours? We are very grateful for your help and look forward to hearing more.\n\nBest wishes,\n${user.displayName}`,
    }
  },
)

const individualOption = ({ individualGuid, displayName }) => ({ value: individualGuid, text: displayName })

export const getParentOptionsByIndividual = createSelector(
  getSortedIndividualsByFamily,
  individualsByFamily => Object.values(individualsByFamily).reduce((acc, individuals) => ({
    ...acc,
    ...individuals.reduce((indAcc, { individualGuid }) => ({
      ...indAcc,
      [individualGuid]: {
        M: individuals.filter(i => SIMPLIFIED_SEX_LOOKUP[i.sex] === 'M' && i.individualGuid !== individualGuid).map(individualOption),
        F: individuals.filter(i => SIMPLIFIED_SEX_LOOKUP[i.sex] === 'F' && i.individualGuid !== individualGuid).map(individualOption),
      },
    }), {}),
  }), {}),
)

// user options selectors
export const getUserOptions = createSelector(
  getUserOptionsByUsername,
  usersOptionsByUsername => Object.values(usersOptionsByUsername).map(
    user => ({ key: user.username, value: user, text: user.email }),
  ),
)

export const getPageHeaderFamily = createSelector(
  getProjectFamiliesByGuid,
  (state, props) => props.match.params.breadcrumbId,
  (familiesByGuid, breadcrumbId) => familiesByGuid[breadcrumbId] || {},
)

export const getPageHeaderAnalysisGroup = createSelector(
  getProjectAnalysisGroupsByGuid,
  (state, props) => props.match.params.breadcrumbId,
  (analysisGroupsByGuid, breadcrumbId) => analysisGroupsByGuid[breadcrumbId] || {},
)

export const getPageHeaderBreadcrumbIdSections = createSelector(
  getCurrentProject,
  getPageHeaderFamily,
  getIndividualsByGuid,
  getPageHeaderAnalysisGroup,
  (state, props) => props.breadcrumb || props.match.params.breadcrumb,
  (state, props) => props.match,
  (project, family, individualsByGuid, analysisGroup, breadcrumb, match) => {
    if (!project) {
      return null
    }

    if (breadcrumb === 'project_page') {
      return []
    }
    if (breadcrumb === 'family_page') {
      const breadcrumbIdSections = [{
        content: `Family: ${family.displayName || ''}`,
        link: `/project/${project.projectGuid}/family_page/${family.familyGuid}`,
      }]
      const { breadcrumbIdSection, breadcrumbIdSubsection } = match.params
      if (breadcrumbIdSection) {
        if (breadcrumbIdSection === 'rnaseq_results') {
          const individualId = individualsByGuid[breadcrumbIdSubsection]?.individualId || ''
          breadcrumbIdSections.push({ content: `RNAseq: ${individualId}` })
        } else {
          breadcrumbIdSections.push({ content: snakecaseToTitlecase(breadcrumbIdSection), link: match.url })
        }
      }
      return breadcrumbIdSections
    }
    if (breadcrumb === 'analysis_group') {
      return [{ content: `Analysis Group: ${analysisGroup.name || ''}`, link: match.url }]
    }
    if (breadcrumb === 'saved_variants') {
      const { variantPage, tag } = match.params
      const path = `/project/${project.projectGuid}/saved_variants`
      const breadcrumbIdSections = [{ content: 'Saved Variants', link: path }]
      if (variantPage === 'variant') {
        breadcrumbIdSections.push({ content: 'Variant', link: match.url })
      } else if (variantPage === 'family') {
        breadcrumbIdSections.push({ content: `Family: ${family.displayName || ''}`, link: `${path}/family/${family.familyGuid}` })
        if (tag) {
          breadcrumbIdSections.push({ content: tag, link: `${path}/family/${family.familyGuid}/${tag}` })
        }
      } else if (variantPage === 'analysis_group') {
        breadcrumbIdSections.push({ content: `Analysis Group: ${analysisGroup.name || ''}`, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}` })
        if (tag) {
          breadcrumbIdSections.push({ content: tag, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}/${tag}` })
        }
      } else if (variantPage) {
        breadcrumbIdSections.push({ content: variantPage, link: match.url })
      }
      return breadcrumbIdSections
    }

    return null
  },
)

const getSearchType = ({ breadcrumb, variantPage }) => {
  if (breadcrumb === 'family_page' || variantPage === 'family') {
    return 'family'
  }
  if (breadcrumb === 'analysis_group' || variantPage === 'analysis_group') {
    return 'analysis_group'
  }
  return 'project'
}

export const getPageHeaderEntityLinks = createSelector(
  getCurrentProject,
  getPageHeaderFamily,
  getPageHeaderAnalysisGroup,
  (state, props) => getSearchType(props.match.params),
  getProjectAnalysisGroupFamiliesByGuid,
  getHasActiveSearchSampleByFamily,
  (project, family, analysisGroup, searchType, familiesByGuid, hasActiveSearchSampleByFamilyGuid) => {
    if (!project) {
      return null
    }

    let searchId = project.projectGuid
    if (searchType === 'family') {
      searchId = family.familyGuid
    } else if (searchType === 'analysis_group') {
      searchId = analysisGroup.analysisGroupGuid
    }

    const familiesToConsider = searchType === 'family' ? [family.familyGuid] : Object.keys(familiesByGuid)
    const disabled = familiesToConsider.every(
      familyGuid => !hasActiveSearchSampleByFamilyGuid[familyGuid],
    )
    const entityLinks = [{
      to: `/variant_search/${searchType === 'analysis_group' ? `project/${project.projectGuid}/` : ''}${searchType}/${searchId}`,
      content: `${snakecaseToTitlecase(searchType)} Variant Search`,
      disabled,
      popup: disabled ?
        `Search is disabled until data is loaded${project.workspaceName ? '. Loading data from AnVIL to seqr is a slow process, and generally takes a week.' : ''}` :
        null,

    }]
    if (project.hasCaseReview) {
      entityLinks.push({
        to: `/project/${project.projectGuid}/case_review`,
        content: 'Case Review',
        activeStyle: { display: 'none' },
      })
    }
    return entityLinks
  },
)

export const getIndividualPhenotypeGeneScores = createSelector(
  getGenesById,
  getIndividualsByGuid,
  getPhenotypeGeneScoresByIndividual,
  (genesById, individualsByGuid, phenotypeGeneScoresByIndividual) => (
    Object.entries(phenotypeGeneScoresByIndividual || {}).reduce((acc, [individualGuid, dataByGene]) => ({
      ...acc,
      [individualGuid]: Object.entries(dataByGene).reduce((acc2, [geneId, dataByTool]) => ([
        ...acc2,
        ...Object.entries(dataByTool).reduce((acc3, [tool, data]) => ([
          ...acc3, ...data.map(d => (
            { ...d, tool, familyGuid: individualsByGuid[individualGuid].familyGuid, gene: genesById[geneId], rowId: `${geneId}-${tool}-${d.diseaseId}` }
          )),
        ]), []),
      ]), []),
    }), {})
  ),
)

export const getTissueOptionsByIndividualGuid = createSelector(
  getRnaSeqDataByIndividual,
  (rnaSeqDataByIndividualGuid) => {
    const tissueTypesByIndividualGuid = Object.entries(rnaSeqDataByIndividualGuid || {}).map(
      ([individualGuid, rnaSeqData]) => ([
        individualGuid,
        [...new Set(Object.values(rnaSeqData || {}).map(Object.values).flat(2).map(({ tissueType }) => tissueType))],
      ]),
    )
    return tissueTypesByIndividualGuid.reduce((acc, [individualGuid, tissueTypes]) => (
      tissueTypes.length > 0 ? {
        ...acc,
        [individualGuid]: tissueTypes.map(tissueType => (
          { key: tissueType, text: TISSUE_DISPLAY[tissueType] || 'Unknown Tissue', value: tissueType }
        )),
      } : acc
    ), {})
  },
)

export const getRnaSeqOutliersByIndividual = createSelector(
  getRnaSeqDataByIndividual,
  rnaSeqDataByIndividual => Object.entries(rnaSeqDataByIndividual).reduce(
    (acc, [individualGuid, rnaSeqData]) => ({
      ...acc,
      [individualGuid]: Object.entries(rnaSeqData).reduce((acc2, [key, data]) => ({
        ...acc2, [key]: Object.values(data).flat(),
      }), {}),
    }), {},
  ),
)
