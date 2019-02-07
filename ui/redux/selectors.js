import { createSelector } from 'reselect'
import { compareObjects } from 'shared/utils/sortUtils'

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
export const getGenesById = state => state.genesById
export const getGenesIsLoading = state => state.genesLoading.isLoading
export const getLocusListsByGuid = state => state.locusListsByGuid
export const getLocusListsIsLoading = state => state.locusListsLoading.isLoading
export const getLocusListIsLoading = state => state.locusListLoading.isLoading
export const getUser = state => state.user

export const getFamilyMatchmakerSubmissions = createSelector(
  getMatchmakerSubmissions,
  (state, props) => props.family,
  (matchmakerSubmissions, family) => {
    return Object.values(matchmakerSubmissions[family.projectGuid] || {}).filter(
      submission => submission.familyId === family.familyId,
    )
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
    }
    return locusList
  },
)
