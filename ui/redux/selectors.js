import { createSelector } from 'reselect'
import orderBy from 'lodash/orderBy'
import uniqBy from 'lodash/uniqBy'

import { compareObjects } from 'shared/utils/sortUtils'
import { toSnakecase } from 'shared/utils/stringUtils'
import {
  NOTE_TAG_NAME,
  EXCLUDED_TAG_NAME,
  REVIEW_TAG_NAME,
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  DISCOVERY_CATEGORY_NAME,
  SORT_BY_FAMILY_GUID,
  VARIANT_SORT_LOOKUP,
  SHOW_ALL,
  VARIANT_EXPORT_DATA,
  familyVariantSamples,
} from 'shared/utils/constants'

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
export const getUsersByUsername = state => state.usersByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getVersion = state => state.meta.version
export const getGoogleLoginEnabled = state => state.meta.googleLoginEnabled
export const getHijakEnabled = state => state.meta.hijakEnabled
export const getProjectGuid = state => state.currentProjectGuid
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
export const getIgvReadsVisibility = state => state.igvReadsVisibility

export const getAnnotationSecondary = (state) => {
  try {
    return !!state.form.variantSearch.values.search.inheritance.annotationSecondary
  }
  catch (err) {
    return false
  }
}

export const getAllUsers = createSelector(
  getUsersByUsername,
  usersByUsername => Object.values(usersByUsername),
)
export const getCurrentProject = createSelector(
  getProjectsByGuid, getProjectGuid, (projectsByGuid, currentProjectGuid) => projectsByGuid[currentProjectGuid],
)

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

export const getIGVSamplesByFamily = createSelector(
  getSortedIndividualsByFamily,
  getIgvSamplesByGuid,
  (individualsByFamily, igvSamplesByGuid) => {
    return Object.entries(individualsByFamily).reduce((acc, [familyGuid, individuals]) => ({
      ...acc,
      [familyGuid]: individuals.reduce((acc2, individual) => [...acc2, ...(individual.igvSampleGuids || [])], []).map(
        sampleGuid => igvSamplesByGuid[sampleGuid]),
    }), {})
  },
)

// Saved variant selectors
export const getSavedVariantTableState = state => (
  state.currentProjectGuid ? state.savedVariantTableState : state.staffSavedVariantTableState
)

export const getPairedSelectedSavedVariants = createSelector(
  getSavedVariantsByGuid,
  (state, props) => props.match.params,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getProjectGuid,
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  (savedVariants, { tag, gene, familyGuid, analysisGroupGuid, variantGuid }, familiesByGuid, analysisGroupsByGuid, projectGuid, tagsByGuid, notesByGuid) => {
    let variants = Object.values(savedVariants)
    if (variantGuid) {
      variants = variants.filter(o => variantGuid.split(',').includes(o.variantGuid))
      return variants.length > 1 ? [variants] : variants
    }

    if (analysisGroupGuid && analysisGroupsByGuid[analysisGroupGuid]) {
      const analysisGroupFamilyGuids = analysisGroupsByGuid[analysisGroupGuid].familyGuids
      variants = variants.filter(o => o.familyGuids.some(fg => analysisGroupFamilyGuids.includes(fg)))
    }
    else if (familyGuid) {
      variants = variants.filter(o => o.familyGuids.includes(familyGuid))
    }
    else if (projectGuid) {
      variants = variants.filter(o => o.familyGuids.some(fg => familiesByGuid[fg].projectGuid === projectGuid))
    }

    const selectedVariantsByGuid = variants.reduce(
      (acc, variant) => ({ ...acc, [variant.variantGuid]: variant }), {})
    const seenCompoundHets = []
    let pairedVariants = variants.reduce((acc, variant) => {
      const variantCompoundHetGuids = [...[
        ...variant.tagGuids.map(t => tagsByGuid[t].variantGuids),
        ...variant.noteGuids.map(n => notesByGuid[n].variantGuids),
      ].filter(variantGuids => variantGuids.length > 1).reduce((guidAcc, variantGuids) =>
        new Set([...guidAcc, ...variantGuids.filter(varGuid => varGuid !== variant.variantGuid)]),
      new Set())].filter(varGuid => selectedVariantsByGuid[varGuid])

      if (variantCompoundHetGuids.length) {
        seenCompoundHets.push(variant.variantGuid)
        return acc.concat(variantCompoundHetGuids.filter(varGuid => !seenCompoundHets.includes(varGuid)).map(
          varGuid => ([variant, selectedVariantsByGuid[varGuid]])))
      }

      acc.push(variant)
      return acc
    }, [])

    if (tag) {
      if (tag === NOTE_TAG_NAME) {
        pairedVariants = pairedVariants.filter(o => (Array.isArray(o) ? o : [o]).some(({ noteGuids }) => noteGuids.length))
      } else if (tag !== SHOW_ALL) {
        pairedVariants = pairedVariants.filter(o => (Array.isArray(o) ? o : [o]).some(({ tagGuids }) => tagGuids.some(tagGuid => tagsByGuid[tagGuid].name === tag)))
      }
    }

    if (gene) {
      pairedVariants = pairedVariants.filter(o => (Array.isArray(o) ? o : [o]).some(
        ({ transcripts }) => gene in (transcripts || {})))
    }

    return pairedVariants
  },
)

export const getPairedFilteredSavedVariants = createSelector(
  getPairedSelectedSavedVariants,
  getSavedVariantTableState,
  getVariantTagsByGuid,
  (state, props) => props.match.params,
  (savedVariants, { categoryFilter = SHOW_ALL, hideExcluded, hideReviewOnly, hideKnownGeneForPhenotype, taggedAfter }, tagsByGuid, { tag, variantGuid }) => {
    if (variantGuid) {
      return savedVariants
    }
    let variantsToShow = savedVariants.map(variant => (Array.isArray(variant) ? variant : [variant]))
    if (hideExcluded) {
      variantsToShow = variantsToShow.filter(variants =>
        variants.every(variant => variant.tagGuids.every(t => tagsByGuid[t].name !== EXCLUDED_TAG_NAME)))
    }
    if (hideReviewOnly) {
      variantsToShow = variantsToShow.filter(variants => variants.every(variant =>
        variant.tagGuids.length !== 1 || tagsByGuid[variant.tagGuids[0]].name !== REVIEW_TAG_NAME,
      ))
    }
    if (!tag) {
      if (hideKnownGeneForPhenotype && categoryFilter === DISCOVERY_CATEGORY_NAME) {
        variantsToShow = variantsToShow.filter(variants => variants.every(variant =>
          variant.tagGuids.every(t => tagsByGuid[t].name !== KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME)))
      }

      if (categoryFilter && categoryFilter !== SHOW_ALL) {
        variantsToShow = variantsToShow.filter(variants => variants.some(
          variant => variant.tagGuids.some(t => tagsByGuid[t].category === categoryFilter)))
      }
    } else if (taggedAfter) {
      const taggedAfterDate = new Date(taggedAfter)
      variantsToShow = variantsToShow.filter(variants => variants.some(variant =>
        variant.tagGuids.find(
          t => tagsByGuid[t].name === tag && new Date(tagsByGuid[t].lastModifiedDate) > taggedAfterDate)))
    }
    return variantsToShow.map(variants => (variants.length === 1 ? variants[0] : variants))
  },
)

export const getSavedVariantVisibleIndices = createSelector(
  getSavedVariantTableState,
  ({ page = 1, recordsPerPage = 25 }) => {
    return [(page - 1) * recordsPerPage, page * recordsPerPage]
  },
)

export const getVisibleSortedSavedVariants = createSelector(
  getPairedFilteredSavedVariants,
  getSavedVariantTableState,
  getSavedVariantVisibleIndices,
  getGenesById,
  getUser,
  (pairedFilteredSavedVariants, { sort = SORT_BY_FAMILY_GUID }, visibleIndices, genesById, user) => {
    // Always secondary sort on xpos
    pairedFilteredSavedVariants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sort](Array.isArray(a) ? a[0] : a, Array.isArray(b) ? b[0] : b, genesById, user) ||
        (Array.isArray(a) ? a[0] : a).xpos - (Array.isArray(b) ? b[0] : b).xpos
    })
    return pairedFilteredSavedVariants.slice(...visibleIndices)
  },
)

export const getSavedVariantTotalPages = createSelector(
  getPairedFilteredSavedVariants, getSavedVariantTableState,
  (filteredSavedVariants, { recordsPerPage = 25 }) => {
    return Math.max(1, Math.ceil(filteredSavedVariants.length / recordsPerPage))
  },
)

const groupByVariantGuids = allObjects =>
  Object.values(allObjects).reduce((acc, o) => {
    const variantGuids = o.variantGuids.sort().join(',')
    if (!acc[variantGuids]) {
      acc[variantGuids] = []
    }
    acc[variantGuids].push(o)
    return acc
  }, {})

const getTagsByVariantGuids = createSelector(
  getVariantTagsByGuid,
  groupByVariantGuids,
)

const getNotesByVariantGuids = createSelector(
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

export const getSavedVariantExportConfig = createSelector(
  getPairedFilteredSavedVariants,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getTagsByVariantGuids,
  getNotesByVariantGuids,
  getCurrentProject,
  getSavedVariantTableState,
  (state, props) => props.match.params,
  (pairedVariants, familiesByGuid, analysisGroupsByGuid, tagsByGuid, notesByGuid, project, tableState, params) => {
    const familyVariants = pairedVariants.reduce(
      (acc, variant) => (Array.isArray(variant) ? acc.concat(variant) : [...acc, variant]), [],
    ).map(({ genotypes, ...variant }) => ({
      ...variant,
      genotypes: Object.keys(genotypes).filter(
        indGuid => variant.familyGuids.some(familyGuid => familiesByGuid[familyGuid].individualGuids.includes(indGuid)),
      ).reduce((acc, indGuid) => ({ ...acc, [indGuid]: genotypes[indGuid] }), {}),
    }))
    const maxGenotypes = Math.max(...familyVariants.map(variant => Object.keys(variant.genotypes).length), 0)

    const familyId = params.familyGuid && params.familyGuid.split(/_(.+)/)[1]
    const analysisGroupName = (analysisGroupsByGuid[params.analysisGroupGuid] || {}).name
    const tagName = params.tag || tableState.categoryFilter || 'All'

    return [{
      name: `${tagName} Variants${familyId ? ` in Family ${familyId}` : ''}${analysisGroupName ? ` in Analysis Group ${analysisGroupName}` : ''}`,
      data: {
        filename: toSnakecase(`saved_${tagName}_variants_${(project || {}).name}${familyId ? `_family_${familyId}` : ''}${analysisGroupName ? `_analysis_group_${analysisGroupName}` : ''}`),
        rawData: familyVariants,
        headers: [
          ...VARIANT_EXPORT_DATA.map(config => config.header),
          ...[...Array(maxGenotypes).keys()].map(i => `sample_${i + 1}:num_alt_alleles:gq:ab`),
        ],
        processRow: variant => ([
          ...VARIANT_EXPORT_DATA.map(config => (
            config.getVal ? config.getVal(variant, tagsByGuid, notesByGuid) : variant[config.header]),
          ),
          ...Object.values(variant.genotypes).map(
            ({ sampleId, numAlt, gq, ab }) => `${sampleId}:${numAlt}:${gq}:${ab}`),
        ]),
      },
    }]
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
