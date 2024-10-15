import { createSelector } from 'reselect'

import { toSnakecase } from 'shared/utils/stringUtils'
import {
  NOTE_TAG_NAME,
  MME_TAG_NAME,
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
  getFamiliesByGuid, getProjectsByGuid, getIndividualsByGuid, getRnaSeqDataByIndividual,
  getPhenotypeGeneScoresByIndividual, getCurrentAnalysisGroupFamilyGuids,
} from 'redux/selectors'

export const getIndividualGeneDataByFamilyGene = createSelector(
  getIndividualsByGuid,
  getRnaSeqDataByIndividual,
  getPhenotypeGeneScoresByIndividual,
  (individualsByGuid, rnaSeqDataByIndividual = {}, phenotypeGeneScoresByIndividual = {}) => (
    Object.entries(individualsByGuid).reduce((acc, [individualGuid, { familyGuid, displayName }]) => {
      const rnaSeqData = rnaSeqDataByIndividual[individualGuid]?.outliers
      const phenotypeGeneScores = phenotypeGeneScoresByIndividual[individualGuid]
      if (rnaSeqData) {
        acc[familyGuid] = acc[familyGuid] || {}
        acc[familyGuid].rnaSeqData = Object.entries(rnaSeqData).reduce(
          (acc2, [geneId, data]) => ({
            ...acc2,
            [geneId]: [
              ...(acc2[geneId] || []),
              ...data.filter(({ isSignificant }) => isSignificant).map(d => ({ ...d, individualName: displayName })),
            ],
          }), acc[familyGuid].rnaSeqData || {},
        )
      }
      if (phenotypeGeneScores) {
        acc[familyGuid] = acc[familyGuid] || {}
        acc[familyGuid].phenotypeGeneScores = Object.entries(phenotypeGeneScores).reduce(
          (acc2, [geneId, dataByTool]) => ({
            ...acc2,
            [geneId]: Object.entries(dataByTool).reduce((acc3, [tool, data]) => ({
              ...acc3,
              [tool]: [...(acc3[tool] || []), ...data.map(d => ({
                ...d, individualName: displayName, rowId: `${displayName}-${d.diseaseId}`,
              }))],
            }), acc2[geneId] || {}),
          }), acc[familyGuid].phenotypeGeneScores || {},
        )
      }
      return acc
    }, {})
  ),
)

// Saved variant selectors
export const getSavedVariantTableState = state => (
  state.currentProjectGuid ? state.savedVariantTableState : state.allProjectSavedVariantTableState
)

const matchingVariants = (variants, matchFunc) => variants.filter(o => (Array.isArray(o) ? o : [o]).some(matchFunc))

// sorts manual variants to top of list, as manual variants are missing all populations
const sortCompHet = (a, b) => (a.populations ? 1 : 0) - (b.populations ? 1 : 0)

const getProjectSavedVariantsSelection = createSelector(
  (state, props) => props.match.params,
  getFamiliesByGuid,
  getCurrentAnalysisGroupFamilyGuids,
  state => state.currentProjectGuid,
  getVariantTagsByGuid,
  ({ tag, familyGuid, analysisGroupGuid, variantGuid }, familiesByGuid, analysisGroupFamilyGuids,
    projectGuid, tagsByGuid) => {
    if (!projectGuid) {
      return null
    }

    let variantFilter
    if (variantGuid) {
      variantFilter = o => variantGuid.split(',').includes(o.variantGuid)
    } else if (analysisGroupFamilyGuids) {
      variantFilter = o => o.familyGuids.some(fg => analysisGroupFamilyGuids.includes(fg))
    } else if (familyGuid) {
      variantFilter = o => o.familyGuids.includes(familyGuid)
    } else {
      variantFilter = o => o.familyGuids.some(fg => familiesByGuid[fg].projectGuid === projectGuid)
    }

    const pairedFilters = []
    if (tag === NOTE_TAG_NAME) {
      pairedFilters.push(({ noteGuids }) => noteGuids.length)
    } else if (tag === MME_TAG_NAME) {
      pairedFilters.push(({ mmeSubmissions = [] }) => mmeSubmissions.length)
    } else if (tag && tag !== SHOW_ALL) {
      pairedFilters.push(({ tagGuids }) => tagGuids.some(tagGuid => tagsByGuid[tagGuid].name === tag))
    } else if (!(familyGuid || analysisGroupGuid)) {
      pairedFilters.push(({ tagGuids }) => tagGuids.length)
    }

    return [variantFilter, pairedFilters]
  },
)

const getSummaryDataSavedVariantsSelection = createSelector(
  (state, props) => props.match.params,
  state => state.currentProjectGuid,
  getVariantTagsByGuid,
  ({ tag, gene }, projectGuid, tagsByGuid) => {
    if (projectGuid) {
      return null
    }
    const pairedFilters = []
    if (gene) {
      pairedFilters.push(({ transcripts }) => gene in (transcripts || {}))
    } if (tag && tag !== SHOW_ALL) {
      const tags = tag.split(';')
      pairedFilters.push(({ tagGuids }) => tags.every(t => tagGuids.some(tagGuid => (
        tagsByGuid[tagGuid][t === DISCOVERY_CATEGORY_NAME ? 'category' : 'name'] === t
      ))))
    }

    const variantFilter = tag || gene ? null : () => false
    return [variantFilter, pairedFilters]
  },
)

export const getPairedSelectedSavedVariants = createSelector(
  getProjectSavedVariantsSelection,
  getSummaryDataSavedVariantsSelection,
  getSavedVariantsByGuid,
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  (projectVariants, summaryDataVariants, savedVariants, tagsByGuid, notesByGuid) => {
    const [variantFilter, pairedFilters] = projectVariants || summaryDataVariants

    let variants = Object.values(savedVariants)
    if (variantFilter) {
      variants = variants.filter(variantFilter)
    }

    const selectedVariantsByGuid = variants.reduce((acc, variant) => ({ ...acc, [variant.variantGuid]: variant }), {})
    const seenPairedGuids = []
    let pairedVariants = variants.reduce((acc, variant) => {
      if (seenPairedGuids.includes(variant.variantGuid)) {
        return acc
      }

      const variantPairGuids = [...[
        ...variant.tagGuids.map(t => tagsByGuid[t].variantGuids),
        ...variant.noteGuids.map(n => notesByGuid[n].variantGuids),
      ].filter(variantGuids => variantGuids.length > 1).reduce(
        (guidAcc, variantGuids) => new Set([
          ...guidAcc, ...variantGuids.filter(varGuid => varGuid !== variant.variantGuid),
        ]), new Set(),
      )].filter(varGuid => selectedVariantsByGuid[varGuid])

      if (variantPairGuids.length) {
        let unseenPairedGuids = variantPairGuids.filter(varGuid => !seenPairedGuids.includes(varGuid))
        seenPairedGuids.push(variant.variantGuid, ...unseenPairedGuids)

        if (unseenPairedGuids.length > 1) {
          // check if variant is part of multiple distinct comp het pairs or a single MNV with 3+ linked variants
          const pairVariant = selectedVariantsByGuid[unseenPairedGuids[0]]
          const separateGuids = unseenPairedGuids.slice(1).filter(varGuid => !(
            pairVariant.tagGuids.some(t => selectedVariantsByGuid[varGuid].tagGuids.includes(t)) ||
            pairVariant.noteGuids.some(n => selectedVariantsByGuid[varGuid].noteGuids.includes(n))))
          if (separateGuids.length) {
            acc.push([variant, ...separateGuids.map(varGuid => selectedVariantsByGuid[varGuid])].sort(sortCompHet))
            unseenPairedGuids = unseenPairedGuids.filter(varGuid => !separateGuids.includes(varGuid))
          }
        }

        acc.push([variant, ...unseenPairedGuids.map(varGuid => selectedVariantsByGuid[varGuid])].sort(sortCompHet))
        return acc
      }

      acc.push(variant)
      return acc
    }, [])

    pairedFilters.forEach((pairedFilter) => {
      pairedVariants = matchingVariants(pairedVariants, pairedFilter)
    })

    return pairedVariants
  },
)

export const getPairedFilteredSavedVariants = createSelector(
  getPairedSelectedSavedVariants,
  getSavedVariantTableState,
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  (state, props) => props.match.params,
  (savedVariants, {
    categoryFilter = SHOW_ALL, hideExcluded, hideReviewOnly, hideKnownGeneForPhenotype, taggedAfter, savedBy,
  }, tagsByGuid, notesByGuid, { tag, variantGuid }) => {
    if (variantGuid) {
      return savedVariants
    }
    let variantsToShow = savedVariants.map(variant => (Array.isArray(variant) ? variant : [variant]))
    if (hideExcluded) {
      variantsToShow = variantsToShow.filter(
        variants => variants.every(variant => variant.tagGuids.every(t => tagsByGuid[t].name !== EXCLUDED_TAG_NAME)),
      )
    }
    if (hideReviewOnly) {
      variantsToShow = variantsToShow.filter(variants => variants.every(
        variant => variant.tagGuids.length !== 1 || tagsByGuid[variant.tagGuids[0]].name !== REVIEW_TAG_NAME,
      ))
    }
    if (savedBy) {
      variantsToShow = variantsToShow.filter(variants => variants.some(
        variant => variant.tagGuids.some(t => tagsByGuid[t].createdBy === savedBy) ||
          variant.noteGuids.some(t => notesByGuid[t].createdBy === savedBy),
      ))
    }
    if (!tag) {
      if (hideKnownGeneForPhenotype && categoryFilter === DISCOVERY_CATEGORY_NAME) {
        variantsToShow = variantsToShow.filter(variants => variants.every(
          variant => variant.tagGuids.every(t => tagsByGuid[t].name !== KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME),
        ))
      }

      if (categoryFilter && categoryFilter !== SHOW_ALL) {
        variantsToShow = variantsToShow.filter(variants => variants.some(
          variant => variant.tagGuids.some(t => tagsByGuid[t].category === categoryFilter),
        ))
      }
    } else if (taggedAfter) {
      const taggedAfterDate = new Date(taggedAfter)
      variantsToShow = variantsToShow.filter(variants => variants.some(
        variant => variant.tagGuids.find(
          t => tagsByGuid[t].name === tag && new Date(tagsByGuid[t].lastModifiedDate) > taggedAfterDate,
        ),
      ))
    }
    return variantsToShow.map(variants => (variants.length === 1 ? variants[0] : variants))
  },
)

export const getSavedVariantVisibleIndices = createSelector(
  getSavedVariantTableState,
  ({ page = 1, recordsPerPage = 25 }) => ([(page - 1) * recordsPerPage, page * recordsPerPage]),
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
  getIndividualGeneDataByFamilyGene,
  (pairedFilteredSavedVariants, { sort = SORT_BY_FAMILY_GUID }, visibleIndices, genesById, user, variantTagsByGuid,
    familiesByGuid, projectsByGuid, individualGeneDataByFamilyGene) => {
    // Always secondary sort on xpos
    pairedFilteredSavedVariants.sort((a, b) => VARIANT_SORT_LOOKUP[sort](
      Array.isArray(a) ? a[0] : a, Array.isArray(b) ? b[0] : b,
      genesById, variantTagsByGuid, user, familiesByGuid, projectsByGuid, individualGeneDataByFamilyGene,
    ) || (Array.isArray(a) ? a[0] : a).xpos - (Array.isArray(b) ? b[0] : b).xpos)
    return pairedFilteredSavedVariants.slice(...visibleIndices)
  },
)

export const getSavedVariantTotalPages = createSelector(
  getPairedFilteredSavedVariants, getSavedVariantTableState,
  (filteredSavedVariants, { recordsPerPage = 25 }) => Math.max(
    1, Math.ceil(filteredSavedVariants.length / recordsPerPage),
  ),
)

const getSavedVariantExportData = createSelector(
  getPairedFilteredSavedVariants,
  getFamiliesByGuid,
  getProjectsByGuid,
  (pairedVariants, familiesByGuid, projectsByGuid) => pairedVariants.reduce(
    (acc, variant) => (Array.isArray(variant) ? acc.concat(variant) : [...acc, variant]), [],
  ).map(({ genotypes, ...variant }) => ({
    ...variant,
    project: projectsByGuid[familiesByGuid[variant.familyGuids[0]].projectGuid].name,
    family: familiesByGuid[variant.familyGuids[0]].displayName,
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
        [...acc, `sample_${i + 1}`, `num_alt_alleles_${i + 1}`, `filters_${i + 1}`, `gq_${i + 1}`, `ab_${i + 1}`]), []),
    ]
  },
)

export const getSavedVariantExportConfig = createSelector(
  getAnalysisGroupsByGuid,
  getVariantTagsByGuid,
  getVariantNotesByGuid,
  getGenesById,
  (state, props) => props.project,
  getSavedVariantTableState,
  (state, props) => props.match.params,
  (analysisGroupsByGuid, tagsByGuid, notesByGuid, genesById, project, tableState, params) => {
    if (project && project.isDemo && !project.allUserDemo) {
      // Do not allow downloads for demo projects
      return null
    }

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
          config.getVal ? config.getVal(variant, tagsByGuid, notesByGuid, genesById) : variant[config.header])),
        ...Object.values(variant.genotypes).reduce(
          (acc, { sampleId, numAlt, gq, ab, filters }) => (
            [...acc, sampleId, numAlt, filters?.join(';') || variant.genotypeFilters, gq, ab]
          ), [],
        ),
      ]),
    }]
  },
)
