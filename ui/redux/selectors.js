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
  VARIANT_EXPORT_DATA,
  familyVariantSamples,
  isActiveVariantSample,
} from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getAnalysisGroupsByGuid = state => state.analysisGroupsByGuid
export const getSavedVariantsByGuid = state => state.savedVariantsByGuid
export const getVariantTagsByGuid = state => state.variantTagsByGuid
export const getVariantNotesByGuid = state => state.variantNotesByGuid
export const getVariantFunctionalDataByGuid = state => state.variantFunctionalDataByGuid
export const getMmeResultsByGuid = state => state.mmeResultsByGuid
export const getGenesById = state => state.genesById
export const getGenesIsLoading = state => state.genesLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getUser = state => state.user
export const getUsersByUsername = state => state.usersByUsername
export const getUserOptionsIsLoading = state => state.userOptionsLoading.isLoading
export const getVersion = state => state.meta.version
export const getProjectGuid = state => state.currentProjectGuid
export const getSavedVariantsIsLoading = state => state.savedVariantsLoading.isLoading
export const getSavedVariantsLoadingError = state => state.savedVariantsLoading.errorMessage
export const getIgvReadsVisibility = state => state.igvReadsVisibility

export const getAnnotationSecondary = (state) => {
  try {
    return state.form.variantSearch.values.search.inheritance.annotationSecondary
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
        sampleGuid => isActiveVariantSample(samplesByGuid[sampleGuid]),
      )),
    }), {})
  },
)

export const getActiveAlignmentSamplesByFamily = createSelector(
  getSortedIndividualsByFamily,
  getSamplesByGuid,
  (individualsByFamily, samplesByGuid) => {
    return Object.entries(individualsByFamily).reduce((acc, [familyGuid, individuals]) => ({
      ...acc,
      [familyGuid]: individuals.reduce((acc2, individual) => [...acc2, ...(individual.sampleGuids || [])], []).map(
        sampleGuid => samplesByGuid[sampleGuid]).filter(
        sample => sample.isActive && sample.datasetType === DATASET_TYPE_READ_ALIGNMENTS,
      ),
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

const getSelectedSavedVariants = createSelector(
  getSavedVariantsByGuid,
  (state, props) => props.match.params,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getProjectGuid,
  getVariantTagsByGuid,
  (savedVariants, { tag, familyGuid, analysisGroupGuid, variantGuid }, familiesByGuid, analysisGroupsByGuid, projectGuid, tagsByGuid) => {
    let variants = Object.values(savedVariants)
    if (variantGuid) {
      return variants.filter(o => variantGuid.split(',').includes(o.variantGuid))
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
        variants = variants.filter(o => o.noteGuids.length)
      } else {
        variants = variants.filter(o => o.tagGuids.some(tagGuid => tagsByGuid[tagGuid].name === tag))
      }
    }

    return variants
  },
)

export const getPairedSelectedSavedVariants = createSelector(
  getSelectedSavedVariants,
  getVariantNotesByGuid,
  getVariantTagsByGuid,
  (selectedSavedVariants, notesByGuid, tagsByGuid) => {
    const selectedVariantsByGuid = selectedSavedVariants.reduce(
      (acc, variant) => ({ ...acc, [variant.variantGuid]: variant }), {})
    const seenCompoundHets = []
    return selectedSavedVariants.reduce((acc, variant) => {
      const variantCompoundHetGuids = [...[
        ...variant.tagGuids.map(t => tagsByGuid[t].variantGuids),
        ...variant.noteGuids.map(n => notesByGuid[n].variantGuids),
      ].filter(variantGuids => variantGuids.length > 1).reduce((guidAcc, variantGuids) =>
        new Set([...guidAcc, ...variantGuids.filter(variantGuid => variantGuid !== variant.variantGuid)]),
      new Set())].filter(variantGuid => selectedVariantsByGuid[variantGuid])

      if (variantCompoundHetGuids.length) {
        seenCompoundHets.push(variant.variantGuid)
        return acc.concat(variantCompoundHetGuids.filter(variantGuid => !seenCompoundHets.includes(variantGuid)).map(
          variantGuid => ([variant, selectedVariantsByGuid[variantGuid]])))
      }

      acc.push(variant)
      return acc
    }, [])
  },
)

export const getPairedFilteredSavedVariants = createSelector(
  getPairedSelectedSavedVariants,
  getSavedVariantCategoryFilter,
  getSavedVariantHideExcluded,
  getSavedVariantHideReviewOnly,
  getSavedVariantHideKnownGeneForPhenotype,
  getSavedVariantTaggedAfter,
  getVariantTagsByGuid,
  (state, props) => props.match.params.tag,
  (state, props) => props.match.params.gene,
  (savedVariants, categoryFilter, hideExcluded, hideReviewOnly, hideKnownGeneForPhenotype, taggedAfter, tagsByGuid, tag, gene) => {
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

      if (categoryFilter !== SHOW_ALL) {
        variantsToShow = variantsToShow.filter(variants => variants.some(
          variant => variant.tagGuids.some(t => tagsByGuid[t].category === categoryFilter)))
      }
    } else {
      if (gene) {
        variantsToShow = variantsToShow.filter(variants => variants.some(variant => gene in variant.transcripts))
      }

      if (taggedAfter) {
        const taggedAfterDate = new Date(taggedAfter)
        variantsToShow = variantsToShow.filter(variants => variants.some(variant =>
          new Date((variant.tagGuids.find(t => tagsByGuid[t].name === tag) || {}).lastModifiedDate) > taggedAfterDate))
      }
    }
    return variantsToShow.map(variants => (variants.length === 1 ? variants[0] : variants))
  },
)

export const getSavedVariantVisibleIndices = createSelector(
  getSavedVariantCurrentPage, getSavedVariantRecordsPerPage,
  (page, recordsPerPage) => {
    return [(page - 1) * recordsPerPage, page * recordsPerPage]
  },
)

export const getVisibleSortedSavedVariants = createSelector(
  getPairedFilteredSavedVariants,
  getSavedVariantSortOrder,
  getSavedVariantVisibleIndices,
  getGenesById,
  getUser,
  (pairedFilteredSavedVariants, sort, visibleIndices, genesById, user) => {
    // Always secondary sort on xpos
    pairedFilteredSavedVariants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sort](Array.isArray(a) ? a[0] : a, Array.isArray(b) ? b[0] : b, genesById, user) ||
        (Array.isArray(a) ? a[0] : a).xpos - (Array.isArray(b) ? b[0] : b).xpos
    })
    return pairedFilteredSavedVariants.slice(...visibleIndices)
  },
)

export const getSavedVariantTotalPages = createSelector(
  getPairedFilteredSavedVariants, getSavedVariantRecordsPerPage,
  (filteredSavedVariants, recordsPerPage) => {
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

export const getVariantTagNotes = createSelector(
  getTagsByVariantGuids,
  getNotesByVariantGuids,
  getFunctionalDataByVariantGuids,
  (state, ownProps) => (Array.isArray(ownProps.variant) ? ownProps.variant : [ownProps.variant]),
  (tagsByGuids, notesByGuids, functionalDataByGuids, variants) => {
    const variantGuids = variants.map(({ variantGuid }) => variantGuid).sort().join(',')
    return {
      variantId: variants.map(({ variantId }) => variantId).join(','),
      variantGuids: variants.every(({ variantGuid }) => variantGuid) ? variantGuids : null,
      tags: tagsByGuids[variantGuids],
      notes: notesByGuids[variantGuids],
      functionalData: functionalDataByGuids[variantGuids],
    }
  },
)

export const getSavedVariantExportConfig = createSelector(
  getPairedFilteredSavedVariants,
  getFamiliesByGuid,
  getTagsByVariantGuids,
  getNotesByVariantGuids,
  (pairedVariants, familiesByGuid, tagsByGuid, notesByGuid) => {
    const familyVariants = pairedVariants.reduce(
      (acc, variant) => (Array.isArray(variant) ? acc.concat(variant) : [...acc, variant]), [],
    ).map(({ genotypes, ...variant }) => ({
      ...variant,
      genotypes: Object.keys(genotypes).filter(
        indGuid => variant.familyGuids.some(familyGuid => familiesByGuid[familyGuid].individualGuids.includes(indGuid)),
      ).reduce((acc, indGuid) => ({ ...acc, [indGuid]: genotypes[indGuid] }), {}),
    }))
    const maxGenotypes = Math.max(...familyVariants.map(variant => Object.keys(variant.genotypes).length), 0)
    return {
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
    }
  },
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
