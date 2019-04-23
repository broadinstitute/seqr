import { createSelector } from 'reselect'
import orderBy from 'lodash/orderBy'

import { compareObjects } from 'shared/utils/sortUtils'
import { familySamplesLoaded } from 'shared/utils/constants'

export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getAnalysisGroupsByGuid = state => state.analysisGroupsByGuid
export const getMatchmakerSubmissions = state => state.matchmakerSubmissions
export const getSavedVariantsByGuid = state => state.savedVariantsByGuid
export const getGenesById = state => state.genesById
export const getGenesIsLoading = state => state.genesLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getUser = state => state.user

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
    const getIndivSortKey = individual => AFFECTED_STATUS_ORDER[individual.affected] || 0

    return Object.entries(familiesByGuid).reduce((acc, [familyGuid, family]) => ({
      ...acc,
      [familyGuid]: orderBy(
        family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]),
        [getIndivSortKey],
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
