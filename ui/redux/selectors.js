import { createSelector } from 'reselect'
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
export const getMatchmakerMatchesLoading = state => state.matchmakerMatchesLoading.isLoading
export const getMonarchMatchesLoading = state => state.monarchMatchesLoading.isLoading
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

export const getFamilyMatchmakerSubmissions = createSelector(
  getMatchmakerSubmissions,
  (state, props) => props.family,
  (matchmakerSubmissions, family) => {
    return Object.values(matchmakerSubmissions[family.projectGuid] || {}).filter(
      submission => submission.familyId === family.familyId,
    )
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
