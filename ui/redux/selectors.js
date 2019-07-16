import { createSelector } from 'reselect'
import orderBy from 'lodash/orderBy'

import { compareObjects } from 'shared/utils/sortUtils'
import {
  NOTE_TAG_NAME,
  EXCLUDED_TAG_NAME,
  REVIEW_TAG_NAME,
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  DISCOVERY_CATEGORY_NAME,
  SORT_BY_FAMILY_GUID,
  VARIANT_SORT_LOOKUP,
  SHOW_ALL,
  DATASET_TYPE_READ_ALIGNMENTS,
  getVariantsExportData,
  familySamplesLoaded,
} from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getAnalysisGroupsByGuid = state => state.analysisGroupsByGuid
export const getSavedVariantsByGuid = state => state.savedVariantsByGuid
export const getMmeResultsByGuid = state => state.mmeResultsByGuid
export const getGenesById = state => state.genesById
export const getGenesIsLoading = state => state.genesLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getUser = state => state.user
export const getUsersByUsername = state => state.usersByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getProjectGuid = state => state.currentProjectGuid
export const getSavedVariantsIsLoading = state => state.savedVariantsLoading.isLoading
export const getIgvReadsVisibility = state => state.igvReadsVisibility

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

/**
 * function that returns a mapping of each familyGuid to an array of individuals in that family.
 * The array of individuals is in sorted order.
 *
 * @param state {object} global Redux state
 */
export const getSortedIndividualsByFamily = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  (familiesByGuid, individualsByGuid) => {
    const AFFECTED_STATUS_ORDER = { A: 1, N: 2, U: 3 }
    const getIndivAffectedSort = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0
    const getIndivMmeSort = individual => (
      individual.mmeDeletedDate ? '2000-01-01' : (individual.mmeSubmittedDate || '1900-01-01')
    )

    return Object.entries(familiesByGuid).reduce((acc, [familyGuid, family]) => ({
      ...acc,
      [familyGuid]: orderBy(
        family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]),
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
      const familySamples = familySamplesLoaded(family, individualsByGuid, samplesByGuid)

      return {
        ...acc,
        [familyGuid]: familySamples.length > 0 ? familySamples[0] : null,
      }
    }, {})
  },
)

export const getAlignmentSamplesByFamily = createSelector(
  getFamiliesByGuid,
  getIndividualsByGuid,
  getSamplesByGuid,
  (familiesByGuid, individualsByGuid, samplesByGuid) => {
    return Object.entries(familiesByGuid).reduce((acc, [familyGuid, family]) => ({
      ...acc,
      [familyGuid]: familySamplesLoaded(family, individualsByGuid, samplesByGuid, DATASET_TYPE_READ_ALIGNMENTS),
    }), {})
  },
)

// Saved variant selectors
export const getSavedVariantTableState = state => state.savedVariantTableState
export const getSavedVariantCategoryFilter = state => state.savedVariantTableState.categoryFilter || SHOW_ALL
export const getSavedVariantSortOrder = state => state.savedVariantTableState.sort || SORT_BY_FAMILY_GUID
export const getSavedVariantHideExcluded = state => state.savedVariantTableState.hideExcluded
export const getSavedVariantHideReviewOnly = state => state.savedVariantTableState.hideReviewOnly
const getSavedVariantHideKnownGeneForPhenotype = state => state.savedVariantTableState.hideKnownGeneForPhenotype
export const getSavedVariantCurrentPage = state => state.savedVariantTableState.page || 1
export const getSavedVariantRecordsPerPage = state => state.savedVariantTableState.recordsPerPage || 25
export const getSavedVariantGeneFilter = state => state.savedVariantTableState.gene
export const getSavedVariantTaggedAfter = state => state.savedVariantTableState.taggedAfter

export const getVariantId = ({ xpos, ref, alt }) => `${xpos}-${ref}-${alt}`

export const getSavedVariantsGroupedByFamilyVariants = createSelector(
  getSavedVariantsByGuid,
  savedVariantsByGuid => Object.values(savedVariantsByGuid).reduce((acc, variant) => {
    variant.familyGuids.forEach((familyGuid) => {
      if (!(familyGuid in acc)) {
        acc[familyGuid] = {}
      }
      acc[familyGuid][getVariantId(variant)] = variant
    })

    return acc

  }, {}),
)

export const getSelectedSavedVariants = createSelector(
  getSavedVariantsByGuid,
  (state, props) => props.match.params,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getProjectGuid,
  (savedVariants, { tag, familyGuid, analysisGroupGuid, variantGuid }, familiesByGuid, analysisGroupsByGuid, projectGuid) => {
    let variants = Object.values(savedVariants)
    if (variantGuid) {
      return variants.filter(o => o.variantGuid === variantGuid)
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

    if (tag) {
      if (tag === NOTE_TAG_NAME) {
        variants = variants.filter(o => o.notes.length)
      } else {
        variants = variants.filter(o => o.tags.some(t => t.name === tag))
      }
    }

    return variants
  },
)

export const getSavedVariantVisibleIndices = createSelector(
  getSavedVariantCurrentPage, getSavedVariantRecordsPerPage,
  (page, recordsPerPage) => {
    return [(page - 1) * recordsPerPage, page * recordsPerPage]
  },
)

export const getFilteredSavedVariants = createSelector(
  getSelectedSavedVariants,
  getSavedVariantCategoryFilter,
  getSavedVariantHideExcluded,
  getSavedVariantHideReviewOnly,
  getSavedVariantHideKnownGeneForPhenotype,
  getSavedVariantGeneFilter,
  getSavedVariantTaggedAfter,
  (state, props) => props.match.params.tag,
  (savedVariants, categoryFilter, hideExcluded, hideReviewOnly, hideKnownGeneForPhenotype, geneFilter, taggedAfter, tag) => {
    let variantsToShow = savedVariants
    if (hideExcluded) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.every(t => t.name !== EXCLUDED_TAG_NAME))
    }
    if (hideReviewOnly) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.length !== 1 || variant.tags[0].name !== REVIEW_TAG_NAME)
    }
    if (!tag) {
      if (hideKnownGeneForPhenotype && categoryFilter === DISCOVERY_CATEGORY_NAME) {
        variantsToShow = variantsToShow.filter(variant => variant.tags.every(t => t.name !== KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME))
      }

      if (categoryFilter !== SHOW_ALL) {
        variantsToShow = variantsToShow.filter(variant => variant.tags.some(t => t.category === categoryFilter))
      }
    } else {
      if (geneFilter) {
        variantsToShow = variantsToShow.filter(variant =>
          (variant.mainTranscript.geneSymbol || '').toLowerCase().startsWith(geneFilter.toLowerCase()))
      }

      if (taggedAfter) {
        const taggedAfterDate = new Date(taggedAfter)
        variantsToShow = variantsToShow.filter(variant =>
          new Date((variant.tags.find(t => t.name === tag) || {}).lastModifiedDate) > taggedAfterDate)
      }
    }
    return variantsToShow
  },
)

export const getVisibleSortedSavedVariants = createSelector(
  getFilteredSavedVariants,
  getSavedVariantSortOrder,
  getSavedVariantVisibleIndices,
  getGenesById,
  getUser,
  (filteredSavedVariants, sort, visibleIndices, genesById, user) => {
    // Always secondary sort on xpos
    filteredSavedVariants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sort](a, b, genesById, user) || a.xpos - b.xpos
    })
    return filteredSavedVariants.slice(...visibleIndices)
  },
)

export const getSavedVariantTotalPages = createSelector(
  getFilteredSavedVariants, getSavedVariantRecordsPerPage,
  (filteredSavedVariants, recordsPerPage) => {
    return Math.max(1, Math.ceil(filteredSavedVariants.length / recordsPerPage))
  },
)

export const getSavedVariantExportConfig = createSelector(
  getFilteredSavedVariants,
  getVariantsExportData,
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
