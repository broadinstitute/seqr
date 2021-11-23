import { createSelector } from 'reselect'

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
} from 'shared/utils/constants'
import {
  getVariantTagsByGuid, getVariantNotesByGuid, getSavedVariantsByGuid, getAnalysisGroupsByGuid, getGenesById, getUser,
  getFamiliesByGuid, getProjectsByGuid,
} from 'redux/selectors'


// Saved variant selectors
export const getSavedVariantTableState = state => (
  state.currentProjectGuid ? state.savedVariantTableState : state.allProjectSavedVariantTableState
)

const matchingVariants = (variants, matchFunc) =>
  variants.filter(o => (Array.isArray(o) ? o : [o]).some(matchFunc))

export const getPairedSelectedSavedVariants = createSelector(
  getSavedVariantsByGuid,
  (state, props) => props.match.params,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  (state, props) => (props.project || {}).projectGuid,
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
      if (seenCompoundHets.includes(variant.variantGuid)) {
        return acc
      }

      const variantCompoundHetGuids = [...[
        ...variant.tagGuids.map(t => tagsByGuid[t].variantGuids),
        ...variant.noteGuids.map(n => notesByGuid[n].variantGuids),
      ].filter(variantGuids => variantGuids.length > 1).reduce((guidAcc, variantGuids) =>
        new Set([...guidAcc, ...variantGuids.filter(varGuid => varGuid !== variant.variantGuid)]),
      new Set())].filter(varGuid => selectedVariantsByGuid[varGuid])

      if (variantCompoundHetGuids.length) {
        const unseenGuids = variantCompoundHetGuids.filter(varGuid => !seenCompoundHets.includes(varGuid))
        const compHet = [variant, ...unseenGuids.map(varGuid => selectedVariantsByGuid[varGuid])].sort((a, b) =>
          // sorts manual variants to top of list, as manual variants are missing all populations
          (a.populations ? 1 : 0) - (b.populations ? 1 : 0),
        )
        acc.push(compHet)
        seenCompoundHets.push(variant.variantGuid, ...unseenGuids)
        return acc
      }

      acc.push(variant)
      return acc
    }, [])

    if (tag === NOTE_TAG_NAME) {
      pairedVariants = matchingVariants(pairedVariants, ({ noteGuids }) => noteGuids.length)
    } else if (tag && tag !== SHOW_ALL) {
      pairedVariants = matchingVariants(
        pairedVariants, ({ tagGuids }) => tagGuids.some(tagGuid => tagsByGuid[tagGuid].name === tag))
    } else if (!(familyGuid || analysisGroupGuid)) {
      pairedVariants = matchingVariants(pairedVariants, ({ tagGuids }) => tagGuids.length)
    }

    if (gene) {
      pairedVariants = matchingVariants(pairedVariants, ({ transcripts }) => gene in (transcripts || {}))
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
  getVariantTagsByGuid,
  getFamiliesByGuid,
  getProjectsByGuid,
  (pairedFilteredSavedVariants, { sort = SORT_BY_FAMILY_GUID }, visibleIndices, genesById, user, variantTagsByGuid, familiesByGuid, projectsByGuid) => {
    // Always secondary sort on xpos
    pairedFilteredSavedVariants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[sort](
        Array.isArray(a) ? a[0] : a, Array.isArray(b) ? b[0] : b, genesById, variantTagsByGuid, user, familiesByGuid, projectsByGuid) ||
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

const getSavedVariantExportData = createSelector(
  getPairedFilteredSavedVariants,
  getFamiliesByGuid,
  (pairedVariants, familiesByGuid) =>
    pairedVariants.reduce(
      (acc, variant) => (Array.isArray(variant) ? acc.concat(variant) : [...acc, variant]), [],
    ).map(({ genotypes, ...variant }) => ({
      ...variant,
      genotypes: Object.keys(genotypes).filter(
        indGuid => variant.familyGuids.some(familyGuid => familiesByGuid[familyGuid].individualGuids.includes(indGuid)),
      ).reduce((acc, indGuid) => ({ ...acc, [indGuid]: genotypes[indGuid] }), {}),
    })),
)

const getSavedVariantExportHeaders = createSelector(
  getSavedVariantExportData,
  (familyVariants) => {
    const maxGenotypes = Math.max(...familyVariants.map(variant => Object.keys(variant.genotypes).length), 0)
    return [
      ...VARIANT_EXPORT_DATA.map(config => config.header),
      ...[...Array(maxGenotypes).keys()].reduce((acc, i) => (
        [...acc, `sample_${i + 1}`, `num_alt_alleles_${i + 1}`, `gq_${i + 1}`, `ab_${i + 1}`]), []),
    ]
  },
)

export const getSavedVariantExportConfig = createSelector(
  getAnalysisGroupsByGuid,
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  (state, props) => props.project,
  getSavedVariantTableState,
  (state, props) => props.match.params,
  (analysisGroupsByGuid, tagsByGuid, notesByGuid, project, tableState, params) => {
    const familyId = params.familyGuid && params.familyGuid.split(/_(.+)/)[1]
    const analysisGroupName = (analysisGroupsByGuid[params.analysisGroupGuid] || {}).name
    const tagName = params.tag || tableState.categoryFilter || 'All'

    return [{
      name: `${tagName} Variants${familyId ? ` in Family ${familyId}` : ''}${analysisGroupName ? ` in Analysis Group ${analysisGroupName}` : ''}`,
      filename: toSnakecase(`saved_${tagName}_variants${project ? `_${project.name}` : ''}${familyId ? `_family_${familyId}` : ''}${analysisGroupName ? `_analysis_group_${analysisGroupName}` : ''}`),
      getRawData: state => getSavedVariantExportData(state, { project, match: { params } }),
      getHeaders: state => getSavedVariantExportHeaders(state, { project, match: { params } }),
      processRow: variant => ([
        ...VARIANT_EXPORT_DATA.map(config => (
          config.getVal ? config.getVal(variant, tagsByGuid, notesByGuid) : variant[config.header]),
        ),
        ...Object.values(variant.genotypes).reduce(
          (acc, { sampleId, numAlt, gq, ab }) => ([...acc, sampleId, numAlt, gq, ab]), []),
      ]),
    }]
  },
)
